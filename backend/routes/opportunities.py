"""
Opportunities routes - Issue #37 (main.py split)
Handles saved opportunities, feedback, search, and job status endpoints.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from auth_service import get_current_user
from credits_service import CreditsService
from datetime import datetime
import asyncio
import uuid
import json
import os
import google.generativeai as genai

router = APIRouter()

# Pydantic models
class SearchRequest(BaseModel):
    prompt: str

class SearchCriteria(BaseModel):
    prompt: str
    focus_areas: Optional[List[str]] = None
    funding_range_min: Optional[int] = None
    funding_range_max: Optional[int] = None
    deadline_days: Optional[int] = None
    target_populations: Optional[List[str]] = None

class JobStatus(BaseModel):
    job_id: str
    status: str  # "running", "completed", "failed"
    progress: int
    current_task: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class FeedbackRequest(BaseModel):
    feedback_type: str  # 'positive' or 'negative'
    user_id: str = "anonymous"

class UpdateOpportunityDescriptionRequest(BaseModel):
    description: str

class UpdateOpportunityNotesRequest(BaseModel):
    notes: str

# Dependencies (set from main.py on startup)
_supabase = None
_supabase_admin = None
_jobs_db = None
_opportunities_db = None
_semantic_service = None
_create_gemini_cli_session = None
_parse_orchestration_response = None
_get_organization_config = None
_grants_service_class = None

def set_dependencies(
    supabase,
    supabase_admin,
    jobs_db: Dict,
    opportunities_db: List,
    semantic_service,
    create_gemini_cli_session,
    parse_orchestration_response,
    get_organization_config,
    grants_service_class=None
):
    """Set shared dependencies from main.py"""
    global _supabase, _supabase_admin, _jobs_db, _opportunities_db
    global _semantic_service, _create_gemini_cli_session, _parse_orchestration_response
    global _get_organization_config, _grants_service_class
    _supabase = supabase
    _supabase_admin = supabase_admin
    _jobs_db = jobs_db
    _opportunities_db = opportunities_db
    _semantic_service = semantic_service
    _create_gemini_cli_session = create_gemini_cli_session
    _parse_orchestration_response = parse_orchestration_response
    _get_organization_config = get_organization_config
    _grants_service_class = grants_service_class


# In-memory feedback store
_feedback_store: Dict[str, Dict[str, int]] = {}


def get_opportunity_feedback_counts(opportunity_id: str) -> Dict[str, int]:
    """Get feedback counts using in-memory store"""
    return _feedback_store.get(opportunity_id, {"positive": 0, "negative": 0})


@router.post("/api/search-opportunities")
async def start_opportunity_search(
    criteria: SearchCriteria,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Start AI-powered opportunity discovery with organization-specific matching"""

    # Check if monthly credits need to be reset
    CreditsService.reset_monthly_credits_if_needed(user_id)

    # Check if user has enough credits for a search (1 credit per search)
    check_result = CreditsService.check_and_deduct_credits(user_id, amount=1, reference_id=None)
    if not check_result["success"]:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail=f"Insufficient credits. {check_result.get('error', 'Please purchase more credits')}"
        )

    job_id = str(uuid.uuid4())

    # Update reference_id with job_id after deduction
    _supabase_admin.table("credit_transactions").update({
        "reference_id": job_id
    }).eq("id", job_id).execute()  # This will need adjustment based on actual transaction ID

    # Initialize job
    _jobs_db[job_id] = {
        "job_id": job_id,
        "status": "running",
        "progress": 0,
        "current_task": "Initializing AI agent...",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "credits_deducted": 1,
        "new_balance": check_result["new_balance"]
    }

    # Start background task with user_id for organization-aware matching
    asyncio.create_task(run_opportunity_search(job_id, criteria, user_id))

    return {
        "job_id": job_id,
        "status": "started",
        "credits_used": 1,
        "new_balance": check_result["new_balance"]
    }


@router.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str, user_id: str = Depends(get_current_user)):
    """Get job status and results (requires authentication)"""
    if job_id not in _jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    return _jobs_db[job_id]


@router.get("/api/opportunities")
async def get_opportunities(user_id: str = Depends(get_current_user)):
    """Get qualified opportunities from org_grants joined with scraped_grants"""
    try:
        # Look up org_id from the user's organization_config record
        org_id = None
        try:
            user_result = _supabase_admin.table("users") \
                .select("organization_id") \
                .eq("id", user_id) \
                .limit(1) \
                .execute()
            if user_result.data:
                org_id = user_result.data[0].get("organization_id")
        except Exception as org_lookup_err:
            print(f"[OPPORTUNITIES] Org lookup error: {org_lookup_err}")

        if not org_id:
            # Fall back to org_config owner lookup
            try:
                org_result = _supabase_admin.table("organization_config") \
                    .select("id") \
                    .eq("owner_id", user_id) \
                    .limit(1) \
                    .execute()
                if org_result.data:
                    org_id = org_result.data[0].get("id")
            except Exception as e2:
                print(f"[OPPORTUNITIES] Org config lookup error: {e2}")

        if not org_id:
            # No org found for this user
            return {"opportunities": [], "message": "Complete your organization setup to see personalized opportunities."}

        # Query org_grants for this org (qualified grants)
        org_grants_result = _supabase_admin.table("org_grants").select("*").eq("org_id", org_id).eq("status", "active").order("match_score", desc=True).execute()
        
        if not org_grants_result.data:
            return {"opportunities": []}
        
        # Get grant_ids to fetch full grant details
        grant_ids = [og["grant_id"] for og in org_grants_result.data]
        
        # Fetch full grant details from scraped_grants
        grants_result = _supabase_admin.table("scraped_grants").select("*").in_("id", grant_ids).execute()
        grants_by_id = {g["id"]: g for g in (grants_result.data or [])}
        
        # Merge org_grants scoring with scraped_grants details
        opportunities = []
        for og in org_grants_result.data:
            grant = grants_by_id.get(og["grant_id"], {})
            if grant:
                opportunity = {
                    "id": og["id"],
                    "opportunity_id": og["grant_id"],
                    "title": grant.get("title", "Unknown"),
                    "funder": grant.get("funder", "Unknown"),
                    "amount": grant.get("amount", 0),
                    "deadline": grant.get("deadline"),
                    "description": grant.get("description", ""),
                    "requirements": grant.get("requirements", []),
                    "contact": grant.get("contact", ""),
                    "application_url": grant.get("application_url", ""),
                    "source": grant.get("source", ""),
                    "match_score": og.get("match_score", 0),
                    "match_reasoning": og.get("match_reasoning", ""),
                    "llm_summary": og.get("llm_summary"),
                    "created_at": og.get("created_at"),
                    "scored_at": og.get("scored_at"),
                    # Additional grant fields
                    "contact_name": grant.get("contact_name"),
                    "contact_phone": grant.get("contact_phone"),
                    "eligibility_explanation": grant.get("eligibility_explanation"),
                    "award_floor": grant.get("award_floor"),
                    "award_ceiling": grant.get("award_ceiling"),
                    "geographic_focus": grant.get("geographic_focus"),
                    "award_type": grant.get("award_type"),
                }
                opportunities.append(opportunity)
        
        return {"opportunities": opportunities}
    except Exception as e:
        print(f"[GET OPPORTUNITIES] Error: {e}")
        # Fallback to empty list if database unavailable
        return {"opportunities": []}


@router.post("/api/opportunities/{opportunity_id}/generate-summary")
async def generate_opportunity_summary(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Generate an AI-powered summary for a saved opportunity"""
    try:
        # Fetch the opportunity from saved_opportunities, filtered by user_id for security
        result = _supabase.table("saved_opportunities").select("*").eq("id", opportunity_id).eq("user_id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        
        opportunity = result.data[0]
        
        # Check if we have a Gemini API key
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
            # Return a structured summary without AI
            description = opportunity.get("description", "No description available")
            requirements = opportunity.get("requirements", [])

            return {
                "summary": {
                    "overview": description[:500] + ("..." if len(description) > 500 else ""),
                    "key_details": [
                        f"💰 Funding Amount: ${opportunity.get('amount', 0):,}",
                        f"🏢 Funder: {opportunity.get('funder', 'N/A')}",
                        f"📅 Deadline: {opportunity.get('deadline', 'N/A')}",
                        f"📊 Match Score: {opportunity.get('match_score', 0)}%",
                        f"📋 Requirements: {len(requirements)} listed" if requirements else "Requirements: See full description"
                    ],
                    "funding_priorities": [
                        "AI analysis not available - API key required",
                        "Review the full description for detailed funding priorities",
                        "Check the funder's website for additional context"
                    ]
                }
            }

        # Use Gemini to generate summary
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')

        prompt = f"""Analyze this grant opportunity and provide a comprehensive understanding of what this RFP offers.

Grant Details:
- Title: {opportunity.get('title', 'N/A')}
- Funder: {opportunity.get('funder', 'N/A')}
- Amount: ${opportunity.get('amount', 0):,}
- Deadline: {opportunity.get('deadline', 'N/A')}
- Match Score: {opportunity.get('match_score', 0)}%
- Description: {opportunity.get('description', 'N/A')}
- Requirements: {json.dumps(opportunity.get('requirements', []))}

Provide a structured analysis in JSON format with these sections:

1. "overview": A comprehensive 4-6 sentence summary that explains:
   - What this grant is funding (the main purpose and scope)
   - Who the intended beneficiaries are
   - What types of projects or activities are eligible
   - Any unique aspects or special focus areas

2. "key_details": Array of 6-8 specific, factual bullet points about:
   - Funding amount and award structure
   - Eligibility requirements
   - Application requirements or process details
   - Timeline and deadline information
   - Geographic restrictions or preferences
   - Priority areas or evaluation criteria
   - Matching funds requirements (if any)
   - Any other important conditions or constraints

3. "funding_priorities": Array of 3-5 bullet points describing what the funder is specifically looking to support or achieve with this grant

Return ONLY valid JSON, no other text."""

        response = model.generate_content(prompt)

        # Parse the response
        summary_text = response.text
        try:
            summary = json.loads(summary_text)
        except (json.JSONDecodeError, TypeError):
            # If JSON parsing fails, create a structured response from the text
            summary = {
                "overview": summary_text[:500],
                "key_details": ["AI-generated insights available in overview"],
                "funding_priorities": ["Review the overview for detailed analysis"]
            }
        
        return {"summary": summary}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.post("/api/opportunities/{opportunity_id}/save")
async def save_opportunity(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Save a specific opportunity to the database with RFP similarity analysis"""
    # Find opportunity in current job results
    opportunity = None
    for job in _jobs_db.values():
        if job.get("result") and job["result"].get("opportunities"):
            for opp in job["result"]["opportunities"]:
                if opp["id"] == opportunity_id:
                    opportunity = opp
                    break

    # If not in search cache, check scraped_grants table
    if not opportunity:
        try:
            result = _supabase.table("scraped_grants").select("*").eq("id", opportunity_id).execute()
            if result.data:
                grant = result.data[0]
                # Convert scraped_grant format to opportunity format
                opportunity = {
                    "id": grant.get("id"),
                    "title": grant.get("title"),
                    "funder": grant.get("funder"),
                    "amount": grant.get("amount"),
                    "deadline": grant.get("deadline"),
                    "description": grant.get("description"),
                    "requirements": grant.get("requirements", []),
                    "contact": grant.get("contact", ""),
                    "application_url": grant.get("application_url", ""),
                    "source": grant.get("source", ""),
                    "contact_name": grant.get("contact_name"),
                    "contact_phone": grant.get("contact_phone"),
                    "contact_description": grant.get("contact_description"),
                    "eligibility_explanation": grant.get("eligibility_explanation"),
                    "cost_sharing": grant.get("cost_sharing", False),
                    "cost_sharing_description": grant.get("cost_sharing_description"),
                    "additional_info_url": grant.get("additional_info_url"),
                    "additional_info_text": grant.get("additional_info_text"),
                    "archive_date": grant.get("archive_date"),
                    "forecast_date": grant.get("forecast_date"),
                    "close_date_explanation": grant.get("close_date_explanation"),
                    "expected_number_of_awards": grant.get("expected_number_of_awards"),
                    "award_floor": grant.get("award_floor"),
                    "award_ceiling": grant.get("award_ceiling"),
                    "attachments": grant.get("attachments", []),
                    "version": grant.get("version"),
                    "last_updated_date": grant.get("last_updated_date")
                }
        except Exception as e:
            print(f"[SAVE] Error checking scraped_grants: {e}")

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found in search results or database")

    try:
        # Generate embedding and find similar RFPs using semantic service
        opportunity_text = f"{opportunity['title']} {opportunity['description']}"
        embedding = None
        similar_rfps = []

        if _semantic_service:
            try:
                # Generate embedding for pgvector storage
                embedding = _semantic_service.get_embedding(opportunity_text)
                print(f"[SAVE] Generated embedding for '{opportunity['title'][:50]}...'")

                # Find similar historical RFPs using semantic search
                similar_rfps = _semantic_service.find_similar_rfps(opportunity_text, limit=5)

                if similar_rfps:
                    print(f"[SAVE] Found {len(similar_rfps)} similar RFPs:")
                    for rfp in similar_rfps:
                        print(f"  - {rfp.get('title', 'Unknown')[:60]}... (similarity: {rfp.get('similarity_score', 0):.2f})")
                else:
                    print("[SAVE] No similar RFPs found in database")
            except Exception as e:
                print(f"[SAVE] Error with semantic service: {e}")

        # Save to scraped_grants table first (consistent with grants.gov flow)
        scraped_data = {
            "opportunity_id": opportunity["id"],
            "title": opportunity["title"],
            "funder": opportunity["funder"],
            "amount": opportunity["amount"],
            "deadline": opportunity["deadline"],
            "description": opportunity["description"],
            "requirements": opportunity.get("requirements", []),
            "contact": opportunity.get("contact", ""),
            "application_url": opportunity.get("application_url", ""),
            "source": opportunity.get("source", "Agent"),  # Mark as Agent-discovered
            "contact_name": opportunity.get("contact_name"),
            "contact_phone": opportunity.get("contact_phone"),
            "contact_description": opportunity.get("contact_description"),
            "eligibility_explanation": opportunity.get("eligibility_explanation"),
            "cost_sharing": opportunity.get("cost_sharing", False),
            "cost_sharing_description": opportunity.get("cost_sharing_description"),
            "additional_info_url": opportunity.get("additional_info_url"),
            "additional_info_text": opportunity.get("additional_info_text"),
            "archive_date": opportunity.get("archive_date"),
            "forecast_date": opportunity.get("forecast_date"),
            "close_date_explanation": opportunity.get("close_date_explanation"),
            "expected_number_of_awards": opportunity.get("expected_number_of_awards"),
            "award_floor": opportunity.get("award_floor"),
            "award_ceiling": opportunity.get("award_ceiling"),
            "attachments": opportunity.get("attachments", []),
            "version": opportunity.get("version"),
            "last_updated_date": opportunity.get("last_updated_date"),
            "geographic_focus": opportunity.get("geographic_focus"),
            "award_type": opportunity.get("award_type"),
            "anticipated_awards": opportunity.get("anticipated_awards"),
            "consortium_required": opportunity.get("consortium_required", False),
            "consortium_description": opportunity.get("consortium_description"),
            "rfp_attachment_requirements": opportunity.get("rfp_attachment_requirements")
        }

        print(f"[SAVE] Saving Agent grant to scraped_grants: {opportunity['title'][:50]}...")

        # Save to scraped_grants table (global grant pool)
        result = _supabase.table("scraped_grants").insert(scraped_data).execute()
        scraped_grant_id = result.data[0]["id"] if result.data else None

        if not scraped_grant_id:
            raise HTTPException(status_code=500, detail="Failed to save to scraped_grants")

        print(f"[SAVE] Saved to scraped_grants with ID: {scraped_grant_id}")

        # Also add to local cache
        _opportunities_db.append(opportunity)

        # Create background job for LLM enhancement (same pattern as save_scraped_grant)
        enhancement_job_id = str(uuid.uuid4())

        _jobs_db[enhancement_job_id] = {
            "job_id": enhancement_job_id,
            "status": "running",
            "progress": 0,
            "current_task": "Starting LLM enhancement...",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "grant_id": scraped_grant_id,
            "grant_title": opportunity.get("title"),
            "source": opportunity.get("source", "Agent"),
            "user_id": user_id  # Store user_id for org-specific matching
        }

        # Import run_llm_enhancement from grants routes
        from routes.grants import run_llm_enhancement

        # Start background LLM enhancement task (will move to saved_opportunities) with org-specific matching
        print(f"[SAVE] Creating background LLM enhancement task. user_id={user_id}, grant_id={scraped_grant_id}")
        asyncio.create_task(run_llm_enhancement(enhancement_job_id, scraped_grant_id, user_id))

        return {
            "status": "processing",
            "opportunity_id": opportunity_id,
            "enhancement_job_id": enhancement_job_id,
            "similar_rfps": similar_rfps,
            "message": f"Opportunity saved! AI enhancement in progress... Found {len(similar_rfps)} similar historical RFPs." if similar_rfps else "Opportunity saved! AI enhancement in progress..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save opportunity: {str(e)}")


@router.patch("/api/opportunities/{opportunity_id}/description")
async def update_opportunity_description(opportunity_id: str, payload: UpdateOpportunityDescriptionRequest, user_id: str = Depends(get_current_user)):
    """Update the description of a saved opportunity"""
    new_description = payload.description.strip()
    if not new_description:
        raise HTTPException(status_code=400, detail="Description cannot be empty")

    updated_at = datetime.now().isoformat()
    updated_record = None
    supabase_error = None

    try:
        result = _supabase.table("saved_opportunities").update({
            "description": new_description,
            "updated_at": updated_at
        }).eq("id", opportunity_id).eq("user_id", user_id).execute()

        if result.data:
            updated_record = result.data[0]
    except Exception as e:
        supabase_error = e

    if not updated_record:
        for opp in _opportunities_db:
            if opp.get("id") == opportunity_id:
                opp["description"] = new_description
                opp["updated_at"] = updated_at
                updated_record = opp
                break

    if not updated_record:
        if supabase_error:
            raise HTTPException(status_code=500, detail=f"Failed to update opportunity description: {supabase_error}")
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return {
        "status": "updated",
        "opportunity_id": opportunity_id,
        "description": updated_record.get("description", new_description),
        "updated_at": updated_record.get("updated_at", updated_at)
    }


@router.patch("/api/opportunities/{opportunity_id}/notes")
async def update_opportunity_notes(opportunity_id: str, payload: UpdateOpportunityNotesRequest, user_id: str = Depends(get_current_user)):
    """Update the notes of a saved opportunity"""
    new_notes = payload.notes.strip() if payload.notes else ""

    updated_at = datetime.now().isoformat()
    updated_record = None
    supabase_error = None

    try:
        result = _supabase.table("saved_opportunities").update({
            "notes": new_notes,
            "updated_at": updated_at
        }).eq("id", opportunity_id).eq("user_id", user_id).execute()

        if result.data:
            updated_record = result.data[0]
    except Exception as e:
        supabase_error = e

    if not updated_record:
        for opp in _opportunities_db:
            if opp.get("id") == opportunity_id:
                opp["notes"] = new_notes
                opp["updated_at"] = updated_at
                updated_record = opp
                break

    if not updated_record:
        if supabase_error:
            raise HTTPException(status_code=500, detail=f"Failed to update opportunity notes: {supabase_error}")
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return {
        "status": "updated",
        "opportunity_id": opportunity_id,
        "notes": updated_record.get("notes", new_notes),
        "updated_at": updated_record.get("updated_at", updated_at)
    }


@router.delete("/api/opportunities/{opportunity_id}")
async def delete_opportunity(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Delete a saved opportunity from the database"""
    try:
        # Delete from saved_opportunities table by opportunity_id, not id
        result = _supabase_admin.table("saved_opportunities").delete().eq("opportunity_id", opportunity_id).eq("user_id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        # Also remove from local cache if exists
        global _opportunities_db
        _opportunities_db = [opp for opp in _opportunities_db if opp.get("opportunity_id") != opportunity_id]

        return {
            "status": "deleted",
            "opportunity_id": opportunity_id,
            "message": "Opportunity successfully removed"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete opportunity: {str(e)}")


@router.post("/api/opportunities/{opportunity_id}/add-to-rfp-db")
async def add_opportunity_to_rfp_database(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """
    Add a saved opportunity to the RFP database for algorithm training.
    This allows users to refine the matching algorithm through feedback.
    """
    try:
        # Fetch the opportunity from saved_opportunities (including existing embedding)
        result = _supabase.table("saved_opportunities").select("*").eq("id", opportunity_id).eq("user_id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        opportunity = result.data[0]

        # Check if already in RFP database
        existing_rfp = _supabase.table("rfps").select("id").eq("title", opportunity["title"]).execute()

        if existing_rfp.data:
            return {
                "status": "already_exists",
                "message": "This opportunity is already in the RFP training database",
                "rfp_id": existing_rfp.data[0]["id"]
            }

        # Reuse existing embedding from saved_opportunities if available
        embedding = opportunity.get("embedding")

        if embedding:
            print(f"[ADD_TO_RFP_DB] Reusing existing embedding for '{opportunity['title'][:50]}...'")
        elif _semantic_service:
            # Only generate new embedding if one doesn't exist
            try:
                opportunity_text = f"{opportunity['title']} {opportunity['description']}"
                embedding = _semantic_service.get_embedding(opportunity_text)
                print(f"[ADD_TO_RFP_DB] Generated new embedding for '{opportunity['title'][:50]}...'")
            except Exception as e:
                print(f"[ADD_TO_RFP_DB] Error generating embedding: {e}")

        # Prepare RFP data
        rfp_data = {
            "title": opportunity["title"],
            "category": opportunity.get("source", "user_feedback"),
            "content": opportunity["description"],
            "file_path": None,  # No file path for user-added opportunities
            "created_at": datetime.now().isoformat()
        }

        # Add embedding if available
        if embedding:
            rfp_data["embedding"] = embedding
            print(f"[ADD_TO_RFP_DB] Including embedding in RFP data")

        # Insert into rfps table
        try:
            rfp_result = _supabase.table("rfps").insert(rfp_data).execute()
        except Exception as db_error:
            # If it's a duplicate key error, the sequence might be out of sync
            error_str = str(db_error)
            if "duplicate key" in error_str.lower() or "23505" in error_str:
                # Try to fix the sequence by selecting max ID and resetting
                print(f"[ADD_TO_RFP_DB] Duplicate key error detected, attempting sequence fix...")

                # Get max ID from table
                max_result = _supabase.table("rfps").select("id").order("id", desc=True).limit(1).execute()
                if max_result.data and len(max_result.data) > 0:
                    max_id = max_result.data[0]["id"]
                    print(f"[ADD_TO_RFP_DB] Max ID in table: {max_id}")

                # Re-raise with helpful message
                raise Exception(
                    f"Database sequence error. The rfps table auto-increment sequence is out of sync. "
                    f"Please run this SQL to fix it: "
                    f"SELECT setval('rfps_id_seq', (SELECT MAX(id) FROM rfps));"
                )
            raise

        if hasattr(rfp_result, 'error') and rfp_result.error:
            raise Exception(f"Database error: {rfp_result.error}")

        return {
            "status": "success",
            "message": "Successfully added to RFP training database",
            "rfp_id": rfp_result.data[0]["id"] if rfp_result.data else None,
            "has_embedding": embedding is not None,
            "opportunity_title": opportunity["title"]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ADD_TO_RFP_DB] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add to RFP database: {str(e)}")


@router.post("/api/opportunities/{opportunity_id}/feedback")
async def submit_opportunity_feedback(opportunity_id: str, feedback: FeedbackRequest):
    """Submit user feedback for an opportunity (thumbs up/down)"""
    try:
        if opportunity_id not in _feedback_store:
            _feedback_store[opportunity_id] = {"positive": 0, "negative": 0}
        
        if feedback.feedback_type in ["positive", "negative"]:
            _feedback_store[opportunity_id][feedback.feedback_type] += 1
        
        return {"message": "Feedback submitted successfully", "status": "success"}
        
    except Exception as e:
        return {"message": f"Feedback received: {feedback.feedback_type}", "status": "success"}


@router.get("/api/opportunities/{opportunity_id}/feedback")
async def get_opportunity_feedback(opportunity_id: str):
    """Get feedback summary for an opportunity"""
    try:
        return get_opportunity_feedback_counts(opportunity_id)
    except Exception as e:
        return {"positive": 0, "negative": 0}


@router.post("/api/opportunities/{opportunity_id}/dismiss")
async def dismiss_opportunity(opportunity_id: str, user_id: str = Depends(get_current_user)):
    """Dismiss an opportunity from the dashboard (mark as not relevant, requires authentication)"""
    try:
        print(f"[DISMISS] Attempting to dismiss opportunity: {opportunity_id}")
        
        # Try to update in scraped_grants table (dashboard uses this)
        scraped_result = _supabase.table("scraped_grants").update({
            "status": "dismissed"
        }).eq("id", opportunity_id).execute()
        
        print(f"[DISMISS] Scraped_grants update result: {len(scraped_result.data or []) > 0}")

        # If not found by id, try by opportunity_id field 
        if not scraped_result.data:
            scraped_alt_result = _supabase.table("scraped_grants").update({
                "status": "dismissed" 
            }).eq("opportunity_id", opportunity_id).execute()
            
            print(f"[DISMISS] Scraped_grants alt update result: {len(scraped_alt_result.data or []) > 0}")
            
            if not scraped_alt_result.data:
                raise HTTPException(status_code=404, detail="Opportunity not found")

        print(f"[DISMISS] Successfully dismissed opportunity {opportunity_id}")
        return {
            "message": "Opportunity dismissed successfully",
            "status": "success",
            "opportunity_id": opportunity_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DISMISS] Error dismissing opportunity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to dismiss opportunity: {str(e)}")


async def run_opportunity_search(job_id: str, criteria: SearchCriteria, user_id: str = None):
    """Execute Claude Code fundraising-cro agent for opportunity discovery with org-aware matching"""
    print(f"[BACKGROUND TASK] Starting run_opportunity_search for job {job_id}, user {user_id}")
    job = _jobs_db[job_id]

    try:
        print(f"[BACKGROUND TASK] Job found, current status: {job['status']}")
        # Update job status
        job["current_task"] = "Initializing fundraising-cro agent..."
        job["progress"] = 10

        # Get organization configuration
        org_config = await _get_organization_config()

        # Build organization context from config
        programs_text = "\n".join([f"- {prog}" for prog in org_config.get("programs", ["Program 1", "Program 2"])])
        metrics = org_config.get("impact_metrics", {})
        metrics_text = "\n".join([f"- {k.replace('_', ' ').title()}: {v}" for k, v in metrics.items()])
        demographics_text = "\n".join([f"- {demo}" for demo in org_config.get("target_demographics", ["Diverse communities"])])

        organization_context = f"""
{org_config.get('name', 'Your Organization')} is a nonprofit organization dedicated to creating positive impact.

Mission: {org_config.get('mission', 'Advancing opportunity through technology and education.')}

Programs:
{programs_text}

Impact:
{metrics_text}

Target Demographics:
{demographics_text}
"""

        job["current_task"] = "Executing fundraising-cro agent search..."
        job["progress"] = 30

        # Use the new Claude Code session creation
        try:
            # Get existing opportunities to avoid duplicates from unified table
            try:
                existing_result = _supabase.table("saved_opportunities").select("title, funder").eq("user_id", user_id).execute()
                existing_opps = [f"{opp['title']} - {opp['funder']}" for opp in existing_result.data]
                existing_list = "; ".join(existing_opps) if existing_opps else "None"
            except Exception:
                existing_list = "None"

            # Create comprehensive prompt for fundraising-cro agent
            orchestration_prompt = f"""You are a fundraising-cro agent for {org_config.get('name', 'the organization')}. Find MULTIPLE (3-5) REAL, CURRENT funding opportunities using web search and research.

Organization Context:
{organization_context}

User Search Request: {criteria.prompt}

Execute this multi-step process:

1. Search current federal databases (GRANTS.gov, NSF, DOL) for relevant funding opportunities
2. Research foundation grants from major funders aligned with the organization's mission
3. Identify corporate funding programs supporting the organization's focus areas
4. Filter for opportunities with deadlines in next 3-6 months and funding >$50k
5. Find at least 3-5 different opportunities from various sources

Existing opportunities to avoid duplicates: {existing_list}

CRITICAL OUTPUT FORMAT - READ CAREFULLY:
You MUST return ONLY raw JSON - NO markdown code blocks, NO explanatory text, NO ```json markers.
Your response should START with {{ and END with }}.

Example of CORRECT output:
{{
  "opportunities": [
    {{
      "id": "unique-id-string",
      "title": "Full grant title",
      "funder": "Organization name",
      "amount": 100000,
      "deadline": "2025-12-31",
      "description": "Detailed description of opportunity",
      "requirements": ["Requirement 1", "Requirement 2"],
      "contact": "email@agency.gov",
      "application_url": "https://...",
      "contact_name": "Contact Person Name or null",
      "contact_phone": "555-1234 or null",
      "contact_description": "Additional contact info or null",
      "eligibility_explanation": "Who can apply or null",
      "cost_sharing": false,
      "cost_sharing_description": "Cost sharing details or null",
      "additional_info_url": "https://... or null",
      "additional_info_text": "Extra info or null",
      "archive_date": "2025-12-31 or null",
      "forecast_date": "2025-01-01 or null",
      "close_date_explanation": "Deadline details or null",
      "expected_number_of_awards": "5-10 or null",
      "award_floor": 50000,
      "award_ceiling": 250000,
      "attachments": [],
      "version": "1 or null",
      "last_updated_date": "2025-01-01 or null",
      "geographic_focus": "State(s) or region(s) where applicants can operate or null",
      "award_type": "Grant, Cooperative Agreement, Loan, Subsidy, etc. or null",
      "anticipated_awards": "Expected number/range of awards or null",
      "consortium_required": false,
      "consortium_description": "Consortium/partnership details or null",
      "rfp_attachment_requirements": "Summary of attachment requirements or null"
    }}
  ]
}}

REQUIREMENTS:
- Return ONLY the JSON object (no markdown blocks, no extra text)
- Start with {{ and end with }}
- All string fields use double quotes
- amount, award_floor, award_ceiling are integers (no commas)
- deadline dates in YYYY-MM-DD format
- Do NOT include match_score (it will be calculated automatically)
- requirements is array of strings
- attachments is empty array [] (no attachment fetching)
- Use null for optional fields if no data available
- Extract ALL fields listed above - these are in the database schema
"""

            job["current_task"] = "Creating Gemini CLI fundraising session..."
            job["progress"] = 50

            # Create Gemini CLI session (with grants service fallback)
            print(f"[Gemini CLI Session] Starting fundraising opportunity discovery...")

            # Use grants service API if available, otherwise fall back to Gemini CLI
            use_api = False  # Set to False to use Gemini CLI instead

            if use_api and _grants_service_class:
                print(f"[Gemini CLI Session] Fetching real grants data...")
                search_keywords = criteria.prompt if criteria.prompt and criteria.prompt != "hi" else "technology workforce development"
                # Clean the search keywords - remove newlines and extra whitespace
                search_keywords = search_keywords.strip()

                grants_service = _grants_service_class(supabase_client=_supabase)
                # Pass user_id for organization-aware matching
                real_grants = grants_service.search_grants(search_keywords, limit=10, user_id=user_id)
                orchestration_result = json.dumps({"opportunities": real_grants})
            else:
                session_result = _create_gemini_cli_session(
                    prompt=orchestration_prompt,
                    session_type="fundraising",
                    timeout=900
                )

                if not session_result['success']:
                    raise Exception(f"Gemini CLI session failed: {session_result['error']}")

                orchestration_result = session_result['output']

            job["current_task"] = "Processing fundraising session results..."
            job["progress"] = 80

            # Parse the orchestrated response
            opportunities = _parse_orchestration_response(orchestration_result)

            # Score opportunities using match_scoring (Gemini is just a scraper)
            if opportunities and _semantic_service:
                from match_scoring import calculate_match_score
                print(f"[SCORING] Scoring {len(opportunities)} opportunities from Gemini CLI agent...")

                for opp in opportunities:
                    try:
                        # Find similar RFPs for this opportunity
                        opp_text = f"{opp.get('title', '')} {opp.get('description', '')}"
                        similar_rfps = _semantic_service.find_similar_rfps(opp_text, limit=5)

                        # Calculate real match score using similar RFPs (with feedback learning)
                        opportunity_id = opp.get('id') or opp.get('opportunity_id')
                        match_score = calculate_match_score(opp, similar_rfps, opportunity_id)
                        opp['match_score'] = match_score

                        print(f"[SCORING] {opp.get('title', 'Unknown')[:60]}... = {match_score}% (found {len(similar_rfps)} similar RFPs)")
                    except Exception as e:
                        print(f"[SCORING] Error scoring opportunity: {e}")
                        opp['match_score'] = opp.get('match_score', 50)  # Keep Claude's estimate as fallback

            # Tag opportunities from Claude Agent with source="Agent"
            if not use_api and opportunities:
                for opp in opportunities:
                    opp['source'] = 'Agent'

        except Exception as e:
            print(f"Orchestration failed: {e}")
            opportunities = []

        # If no opportunities found, return empty result
        if not opportunities:
            opportunities = []

        # Complete job with opportunities for user review
        saved_opportunities = opportunities
        job["status"] = "completed"
        job["progress"] = 100
        job["current_task"] = "Search completed successfully"
        job["result"] = {
            "opportunities": opportunities,
            "saved_opportunities": len(saved_opportunities),
            "total_found": len(opportunities),
            "search_criteria": criteria.model_dump(),
            "completed_at": datetime.now().isoformat()
        }

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["current_task"] = f"Error: {str(e)}"
