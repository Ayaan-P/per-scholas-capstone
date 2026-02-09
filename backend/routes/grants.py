"""
Grants routes - Issue #37 (main.py split)
Extracted: scraped grants listing and LLM enhancement

Routes:
- GET /api/scraped-grants - List grants with personalized match scores
- POST /api/scraped-grants/{grant_id}/save - Start LLM enhancement job
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any
from auth_service import get_current_user, optional_token
from datetime import datetime
import asyncio
import uuid

router = APIRouter(prefix="/api", tags=["grants"])

# Dependencies injected from main.py
_supabase = None
_supabase_admin = None
_jobs_db = None


def set_dependencies(supabase, supabase_admin, jobs_db):
    """Inject dependencies from main.py"""
    global _supabase, _supabase_admin, _jobs_db
    _supabase = supabase
    _supabase_admin = supabase_admin
    _jobs_db = jobs_db


async def run_llm_enhancement(job_id: str, grant_id: str, user_id: str = None):
    """Background task for LLM enhancement with progress updates"""
    job = _jobs_db[job_id]

    try:
        from llm_enhancement_service import enhance_and_save_grant

        # Update progress
        job["current_task"] = "Generating AI summary..."
        job["progress"] = 25

        # Run LLM enhancement with user_id for org-specific matching
        # Use admin client to bypass RLS and properly insert with user_id
        enhanced_grant = await enhance_and_save_grant(grant_id, _supabase_admin, user_id)

        # Update progress
        job["current_task"] = "Extracting tags and reasoning..."
        job["progress"] = 75

        # Mark complete
        job["status"] = "completed"
        job["progress"] = 100
        job["current_task"] = "Grant saved with AI insights!"
        job["result"] = {
            "grant_id": grant_id,
            "opportunity_id": enhanced_grant.get("opportunity_id"),
            "llm_summary": enhanced_grant.get("llm_summary"),
            "tags": enhanced_grant.get("tags", []),
            "detailed_reasoning": enhanced_grant.get("detailed_match_reasoning"),
            "completed_at": datetime.now().isoformat()
        }

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["current_task"] = f"Error: {str(e)}"
        print(f"[LLM Enhancement Job] Failed: {e}")


@router.get("/scraped-grants")
async def get_scraped_grants(
    source: Optional[str] = None,
    user_id: Optional[str] = Depends(optional_token)
):
    """
    Get grants collected by scheduled scrapers with personalized match scores (if authenticated)

    Args:
        source: Filter by data source (grants_gov, state, local, etc.)
        user_id: Optional authenticated user ID (from JWT token) - if provided, returns personalized scores
    """
    try:
        # Fetch grants from database
        query = _supabase.table("scraped_grants").select("*", count="exact")

        if source:
            query = query.eq("source", source)

        query = query.order("created_at", desc=True)

        result = query.execute()
        grants = result.data

        # Calculate personalized match scores if user is authenticated
        org_profile = None
        if user_id:
            try:
                from organization_matching_service import OrganizationMatchingService
                from match_scoring import calculate_match_score

                matching_service = OrganizationMatchingService(_supabase)
                org_profile = await matching_service.get_organization_profile(user_id)

                if org_profile:
                    # Recalculate match scores based on organization profile
                    for grant in grants:
                        # Calculate base keyword matching score using organization's keywords
                        primary_keywords, secondary_keywords = matching_service.build_search_keywords(org_profile)

                        # Get grant text
                        title_lower = (grant.get('title') or '').lower()
                        desc_lower = (grant.get('description') or '').lower()
                        full_text = title_lower + ' ' + desc_lower

                        # Count keyword matches
                        primary_matches = sum(1 for keyword in primary_keywords if keyword in full_text)
                        secondary_matches = sum(1 for keyword in secondary_keywords if keyword in full_text)

                        # Calculate keyword score (0-100)
                        if primary_matches >= 2:
                            keyword_score = min(100, (primary_matches * 15) + (secondary_matches * 3))
                        elif primary_matches == 1:
                            keyword_score = min(50, primary_matches * 15 + (secondary_matches * 2))
                        else:
                            keyword_score = max(10, secondary_matches * 2)

                        # For now, use 0 for semantic similarity (would need RFP embeddings)
                        semantic_score = 0

                        # Calculate organization-specific match score
                        org_match = matching_service.calculate_organization_match_score(
                            org_profile,
                            {
                                'title': grant.get('title'),
                                'description': grant.get('description'),
                                'synopsis': grant.get('description'),
                                'estimated_funding_min': grant.get('award_floor'),
                                'estimated_funding_max': grant.get('award_ceiling') or grant.get('amount'),
                                'deadline': grant.get('deadline'),
                                'geographic_focus': None,  # Could extract from grant if available
                            },
                            keyword_score,
                            semantic_score
                        )

                        # Update the match_score field with personalized score
                        grant['match_score'] = int(org_match['overall_score'])
                        grant['match_breakdown'] = {
                            'keyword_matching': org_match['keyword_matching'],
                            'funding_alignment': org_match['funding_alignment'],
                            'deadline_feasibility': org_match['deadline_feasibility'],
                            'demographic_alignment': org_match['demographic_alignment'],
                            'geographic_alignment': org_match['geographic_alignment'],
                        }
            except Exception as e:
                print(f"[GET SCRAPED GRANTS] Error calculating personalized scores: {e}")
                # Continue with generic scores from database

        return {
            "grants": grants,
            "count": len(grants),
            "total": result.count if hasattr(result, 'count') else len(grants),
            "source": source,
            "personalized": org_profile is not None
        }
    except Exception as e:
        print(f"[GET SCRAPED GRANTS] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch scraped grants: {str(e)}")


@router.post("/scraped-grants/{grant_id}/save")
async def save_scraped_grant(grant_id: str, user_id: str = Depends(get_current_user)):
    """Start LLM enhancement job for a scraped grant (async with progress tracking)"""
    print(f"[SAVE GRANT] Request received for grant_id={grant_id}, user_id={user_id}")
    try:
        # Fetch the grant from scraped_grants table
        result = _supabase.table("scraped_grants").select("*").eq("id", grant_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Grant not found")

        grant = result.data[0]

        # Check if already saved in unified table by this user
        existing = _supabase.table("saved_opportunities").select("id").eq("opportunity_id", grant["opportunity_id"]).eq("user_id", user_id).execute()

        if existing.data:
            return {
                "status": "already_saved",
                "message": "This grant is already in your pipeline"
            }

        # Create background job for LLM enhancement
        job_id = str(uuid.uuid4())

        _jobs_db[job_id] = {
            "job_id": job_id,
            "status": "running",
            "progress": 0,
            "current_task": "Starting LLM enhancement...",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "grant_id": grant_id,
            "grant_title": grant.get("title"),
            "source": grant.get("source", "grants_gov"),  # Include source field for LLM enhancement
            "user_id": user_id  # Store user_id for org-specific matching
        }

        # Start background task with user_id for org-specific matching
        asyncio.create_task(run_llm_enhancement(job_id, grant_id, user_id))

        return {
            "status": "processing",
            "job_id": job_id,
            "message": "Grant is being enhanced with AI insights...",
            "grant_title": grant.get("title")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start enhancement: {str(e)}")
