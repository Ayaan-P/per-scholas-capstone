"""Dashboard and analytics routes"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
import httpx
import os

from auth_service import get_current_user

router = APIRouter(prefix="/api", tags=["dashboard"])

# These will be injected from main.py
supabase = None
jobs_db = None


def set_dependencies(db, jobs):
    """Allow main.py to inject dependencies"""
    global supabase, jobs_db
    supabase = db
    jobs_db = jobs


async def get_user_org_id(user_id: str) -> int:
    """Get organization ID for authenticated user"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_key or not supabase_url:
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{supabase_url}/rest/v1/users?select=organization_id&id=eq.{user_id}",
            headers=headers
        )
    
    if response.status_code != 200:
        # Fallback to saved_opportunities if no org
        return None
    
    data = response.json()
    if not data or not data[0].get("organization_id"):
        return None
    
    return int(data[0]["organization_id"])


@router.get("/dashboard/stats")
async def get_dashboard_stats(user_id: str = Depends(get_current_user)):
    """Get dashboard statistics"""
    try:
        org_id = await get_user_org_id(user_id)
        
        if org_id:
            # New: Read from org_grants (org-specific scored grants)
            org_grants_result = supabase.table("org_grants") \
                .select("grant_id, match_score, status, scraped_grants(amount)") \
                .eq("org_id", org_id) \
                .neq("status", "dismissed") \
                .execute()
            
            grants = org_grants_result.data
            total_opportunities = len(grants)
            total_funding = sum(
                grant.get("scraped_grants", {}).get("amount", 0) 
                for grant in grants 
                if grant.get("scraped_grants")
            )
            avg_match_score = sum(grant.get("match_score", 0) for grant in grants) // len(grants) if grants else 0
        else:
            # Fallback: Read from saved_opportunities (legacy)
            opportunities_result = supabase.table("saved_opportunities").select("amount").eq("user_id", user_id).execute()
            opportunities = opportunities_result.data
            
            total_opportunities = len(opportunities)
            total_funding = sum(opp.get("amount", 0) for opp in opportunities)
            avg_match_score = 85

        # Get proposals count
        proposals_result = supabase.table("proposals").select("id, status").execute()
        proposals = proposals_result.data

        total_proposals = len(proposals)
        approved_proposals = len([p for p in proposals if p.get("status") == "approved"])
        submitted_proposals = len([p for p in proposals if p.get("status") in ["submitted", "approved"]])

        return {
            "totalOpportunities": total_opportunities,
            "totalProposals": total_proposals,
            "totalFunding": total_funding,
            "recentSearches": len(jobs_db) if jobs_db else 0,
            "avgMatchScore": avg_match_score
        }
    except Exception as e:
        print(f"[DASHBOARD] Error: {e}")
        return {
            "totalOpportunities": 0,
            "totalProposals": 0,
            "totalFunding": 0,
            "recentSearches": 0,
            "avgMatchScore": 0
        }


@router.get("/dashboard/activity")
async def get_dashboard_activity():
    """Get recent activity"""
    activities = []

    if jobs_db:
        # Add recent job activities
        for job in list(jobs_db.values())[-5:]:
            if job.get("status") == "completed":
                activities.append({
                    "id": job["job_id"],
                    "type": "search",
                    "description": f"Completed search: {job.get('result', {}).get('total_found', 0)} opportunities found",
                    "timestamp": job.get("created_at", datetime.now().isoformat())
                })

    return {"activities": activities}


@router.get("/analytics")
async def get_analytics(range: str = "30d"):
    """Get analytics data"""
    jobs_count = len(jobs_db) if jobs_db else 0
    completed_jobs = len([j for j in jobs_db.values() if j.get("status") == "completed"]) if jobs_db else 0
    
    return {
        "searchMetrics": {
            "totalSearches": jobs_count,
            "successfulSearches": completed_jobs,
            "avgOpportunitiesPerSearch": 4.2,
            "avgMatchScore": 85
        },
        "opportunityMetrics": {
            "totalOpportunities": 15,
            "savedOpportunities": 8,
            "totalFundingValue": 1250000,
            "avgFundingAmount": 156250
        },
        "proposalMetrics": {
            "totalProposals": 3,
            "submittedProposals": 2,
            "approvedProposals": 1,
            "successRate": 33
        },
        "timeSeriesData": [
            {"date": (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d"), "searches": 2, "opportunities": 8, "proposals": 1},
            {"date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"), "searches": 1, "opportunities": 4, "proposals": 0},
            {"date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"), "searches": 3, "opportunities": 12, "proposals": 2},
            {"date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"), "searches": 1, "opportunities": 3, "proposals": 0},
            {"date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"), "searches": 2, "opportunities": 7, "proposals": 1},
            {"date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), "searches": 1, "opportunities": 5, "proposals": 0},
            {"date": datetime.now().strftime("%Y-%m-%d"), "searches": 0, "opportunities": 0, "proposals": 0}
        ],
        "topFunders": [
            {"name": "U.S. Department of Labor", "opportunityCount": 3, "totalFunding": 450000},
            {"name": "Gates Foundation", "opportunityCount": 2, "totalFunding": 300000},
            {"name": "Ford Foundation", "opportunityCount": 2, "totalFunding": 250000},
            {"name": "JPMorgan Chase Foundation", "opportunityCount": 1, "totalFunding": 200000},
            {"name": "Google.org", "opportunityCount": 1, "totalFunding": 75000}
        ]
    }
