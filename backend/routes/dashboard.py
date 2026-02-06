"""Dashboard and analytics routes"""

from fastapi import APIRouter, Depends
from datetime import datetime, timedelta

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


@router.get("/dashboard/stats")
async def get_dashboard_stats(user_id: str = Depends(get_current_user)):
    """Get dashboard statistics"""
    try:
        # Get opportunities count and funding from unified table
        opportunities_result = supabase.table("saved_opportunities").select("amount").eq("user_id", user_id).execute()
        opportunities = opportunities_result.data

        # Get proposals count
        proposals_result = supabase.table("proposals").select("id, status").execute()
        proposals = proposals_result.data

        # Calculate stats
        total_opportunities = len(opportunities)
        total_proposals = len(proposals)
        total_funding = sum(opp.get("amount", 0) for opp in opportunities)

        approved_proposals = len([p for p in proposals if p.get("status") == "approved"])
        submitted_proposals = len([p for p in proposals if p.get("status") in ["submitted", "approved"]])

        return {
            "totalOpportunities": total_opportunities,
            "totalProposals": total_proposals,
            "totalFunding": total_funding,
            "recentSearches": len(jobs_db) if jobs_db else 0,
            "avgMatchScore": 85
        }
    except Exception as e:
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
