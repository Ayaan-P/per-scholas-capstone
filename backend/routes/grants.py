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
    limit: int = 150,
    offset: int = 0,
    user_id: Optional[str] = Depends(optional_token)
):
    """
    Get grants collected by scheduled scrapers with personalized match scores (if authenticated)

    Args:
        source: Filter by data source (grants_gov, state, local, etc.)
        limit: Maximum number of grants to return (default 150)
        offset: Pagination offset (default 0)
        user_id: Optional authenticated user ID (from JWT token) - if provided, returns personalized scores
    """
    try:
        # Fetch grants from database with pagination
        query = _supabase.table("scraped_grants").select("*", count="exact")

        if source:
            query = query.eq("source", source)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

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
                    # Filter out grants matching org's excluded keywords before scoring
                    filtered_grants = []
                    for grant in grants:
                        should_exclude, exclude_reason = matching_service.should_filter_grant(org_profile, grant)
                        if should_exclude:
                            print(f"[GET SCRAPED GRANTS] Filtering out grant {grant.get('id')}: {exclude_reason}")
                        else:
                            filtered_grants.append(grant)
                    grants = filtered_grants

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

        total = result.count if (hasattr(result, 'count') and result.count is not None) else len(grants)
        return {
            "grants": grants,
            "count": len(grants),
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(grants)) < total,
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


async def _get_user_org_id(user_id: str) -> Optional[int]:
    """Get organization ID for authenticated user"""
    try:
        result = _supabase.table("users").select("organization_id").eq("id", user_id).limit(1).execute()
        if result.data and result.data[0].get("organization_id"):
            return int(result.data[0]["organization_id"])
    except Exception as e:
        print(f"[GET USER ORG] Error: {e}")
    return None


@router.get("/my-grants")
async def get_my_grants(
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 150,
    offset: int = 0,
    search: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Get grants scored for the user's organization (from org_grants table).
    
    This returns pre-computed qualification scores from the qualification agent.
    Falls back to scraped_grants with on-the-fly scoring if no org_grants exist.
    
    Args:
        status: Filter by status (active, dismissed, saved, applied, won, lost, in_progress, submitted)
        min_score: Minimum match score threshold (0-100)
        search: Text search across title, funder, description (case-insensitive)
    """
    try:
        org_id = await _get_user_org_id(user_id)
        
        if not org_id:
            # User has no org, fall back to generic grants
            return await get_scraped_grants(user_id=user_id)
        
        # Try org_grants first (pre-computed scores)
        query = _supabase.table("org_grants") \
            .select("""
                id,
                grant_id,
                status,
                match_score,
                llm_summary,
                match_reasoning,
                key_tags,
                effort_estimate,
                winning_strategies,
                scored_at,
                scraped_grants (
                    id,
                    opportunity_id,
                    title,
                    funder,
                    agency,
                    amount,
                    amount_min,
                    amount_max,
                    deadline,
                    description,
                    eligibility,
                    requirements,
                    application_url,
                    source,
                    created_at,
                    updated_at,
                    posted_date,
                    category_id
                )
            """) \
            .eq("org_id", org_id)
        
        # Apply filters
        if status:
            query = query.eq("status", status)
        else:
            # Default: show active (not dismissed)
            query = query.neq("status", "dismissed")
        
        if min_score is not None:
            query = query.gte("match_score", min_score)
        
        # Order by score descending with pagination
        query = query.order("match_score", desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        org_grants = result.data or []
        
        if org_grants:
            # Transform to flat grant format for frontend compatibility
            grants = []
            for og in org_grants:
                grant_data = og.get("scraped_grants", {})
                if not grant_data:
                    continue
                
                # Merge org_grants data with scraped_grants data
                grant = {
                    **grant_data,
                    "match_score": og.get("match_score", 0),
                    "match_reasoning": og.get("match_reasoning"),
                    "llm_summary": og.get("llm_summary"),
                    "key_tags": og.get("key_tags", []),
                    "effort_estimate": og.get("effort_estimate"),
                    "winning_strategies": og.get("winning_strategies", []),
                    "org_status": og.get("status"),
                    "scored_at": og.get("scored_at"),
                    "org_grant_id": og.get("id"),
                }
                grants.append(grant)
            
            # Apply excluded_keywords filter to pre-scored org_grants
            try:
                from organization_matching_service import OrganizationMatchingService
                matching_service = OrganizationMatchingService(_supabase)
                org_profile = await matching_service.get_organization_profile(user_id)
                if org_profile:
                    filtered = []
                    for grant in grants:
                        should_exclude, exclude_reason = matching_service.should_filter_grant(org_profile, grant)
                        if not should_exclude:
                            filtered.append(grant)
                        else:
                            print(f"[MY GRANTS] Excluding grant {grant.get('id')}: {exclude_reason}")
                    grants = filtered
            except Exception as exc:
                print(f"[MY GRANTS] Excluded keyword filter error (non-fatal): {exc}")

            # Apply server-side text search
            if search:
                search_lower = search.lower()
                grants = [
                    g for g in grants
                    if search_lower in (g.get("title") or "").lower()
                    or search_lower in (g.get("funder") or "").lower()
                    or search_lower in (g.get("description") or "").lower()
                    or search_lower in (g.get("agency") or "").lower()
                ]

            # has_more: if DB returned the full limit, there may be more pages
            # (Python-side filters may reduce the count, but we conservatively signal more)
            db_returned_full_page = len(org_grants) >= limit

            return {
                "grants": grants,
                "count": len(grants),
                "has_more": db_returned_full_page,
                "limit": limit,
                "offset": offset,
                "org_id": org_id,
                "source": "org_grants",
                "personalized": True
            }
        
        # No org_grants yet, fall back to scraped_grants with on-the-fly scoring
        print(f"[MY GRANTS] No org_grants for org {org_id}, falling back to scraped_grants")
        return await get_scraped_grants(user_id=user_id)
        
    except Exception as e:
        print(f"[MY GRANTS] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch grants: {str(e)}")


@router.post("/my-grants/{grant_id}/dismiss")
async def dismiss_grant(
    grant_id: str,
    reason: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Dismiss a grant from the user's dashboard.
    
    Updates the org_grants status to 'dismissed' so it won't show up again.
    """
    try:
        org_id = await _get_user_org_id(user_id)
        
        if not org_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Update org_grants status
        result = _supabase.table("org_grants") \
            .update({
                "status": "dismissed",
                "dismissed_at": datetime.now().isoformat(),
                "dismissed_by": user_id,
                "dismissed_reason": reason
            }) \
            .eq("org_id", org_id) \
            .eq("grant_id", grant_id) \
            .execute()
        
        if not result.data:
            # Grant not in org_grants yet, create dismissed entry
            _supabase.table("org_grants").insert({
                "org_id": org_id,
                "grant_id": grant_id,
                "status": "dismissed",
                "dismissed_at": datetime.now().isoformat(),
                "dismissed_by": user_id,
                "dismissed_reason": reason,
                "match_score": 0
            }).execute()
        
        return {"status": "dismissed", "grant_id": grant_id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DISMISS GRANT] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to dismiss grant: {str(e)}")


# Valid pipeline statuses
VALID_GRANT_STATUSES = {"active", "saved", "in_progress", "submitted", "won", "lost", "dismissed"}


@router.patch("/my-grants/{grant_id}/status")
async def update_grant_status(
    grant_id: str,
    status: str,
    notes: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Update the pipeline status of a grant in the user's org.
    
    Status values:
      active     — visible in dashboard (default)
      saved      — bookmarked / watching
      in_progress — application being worked on
      submitted  — application submitted
      won        — grant awarded 🎉
      lost       — not awarded
      dismissed  — hidden from dashboard
    """
    if status not in VALID_GRANT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_GRANT_STATUSES))}"
        )

    try:
        org_id = await _get_user_org_id(user_id)
        if not org_id:
            raise HTTPException(status_code=400, detail="User has no organization")

        update_data: Dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
        }

        # Carry over status-specific timestamps
        if status == "dismissed":
            update_data["dismissed_at"] = datetime.now().isoformat()
            update_data["dismissed_by"] = user_id
            if notes:
                update_data["dismissed_reason"] = notes
        elif status == "submitted":
            update_data["submitted_at"] = datetime.now().isoformat()
        elif status == "won":
            update_data["won_at"] = datetime.now().isoformat()

        # Try update first
        result = _supabase.table("org_grants") \
            .update(update_data) \
            .eq("org_id", org_id) \
            .eq("grant_id", grant_id) \
            .execute()

        if not result.data:
            # Grant not yet in org_grants — create a minimal record
            insert_data = {
                "org_id": org_id,
                "grant_id": grant_id,
                "match_score": 0,
                **update_data,
            }
            _supabase.table("org_grants").insert(insert_data).execute()

        return {
            "status": status,
            "grant_id": grant_id,
            "org_id": org_id,
            "updated_at": update_data["updated_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPDATE GRANT STATUS] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update grant status: {str(e)}")
