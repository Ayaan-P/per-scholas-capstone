"""
Feedback routes - Track user actions for adaptive learning
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from auth_service import get_current_user
from adaptive_scoring import AdaptiveScoringAgent
import os

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

# Module-level dependencies
_supabase = None

def set_dependencies(supabase):
    """Set dependencies from main app"""
    global _supabase
    _supabase = supabase


class GrantFeedback(BaseModel):
    grant_id: str
    action: str  # "saved", "dismissed", "applied", "won", "lost"
    note: Optional[str] = None


async def get_user_org_id(user_id: str) -> str:
    """Get organization ID for authenticated user"""
    import httpx
    
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
        raise HTTPException(status_code=404, detail="User not found")
    
    data = response.json()
    if not data or not data[0].get("organization_id"):
        raise HTTPException(status_code=400, detail="User has no organization")
    
    return str(data[0]["organization_id"])


@router.post("/grant")
async def record_grant_feedback(
    feedback: GrantFeedback,
    user_id: str = Depends(get_current_user)
):
    """
    Record user feedback on a grant for adaptive learning.
    
    The scoring agent uses this feedback to improve its accuracy over time.
    """
    org_id = await get_user_org_id(user_id)
    
    # Get the grant and its predicted score from org_grants
    try:
        result = _supabase.table("org_grants") \
            .select("match_score, grant_id, scraped_grants(*)") \
            .eq("org_id", org_id) \
            .eq("grant_id", feedback.grant_id) \
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Grant not found for this org")
        
        grant_data = result.data[0]
        predicted_score = grant_data.get("match_score", 0)
        grant_info = grant_data.get("scraped_grants", {})
        
        # Initialize adaptive scoring agent
        adaptive_agent = AdaptiveScoringAgent(org_id)
        
        # Record feedback
        adaptive_agent.record_feedback(
            grant_id=feedback.grant_id,
            grant=grant_info,
            predicted_score=predicted_score,
            action=feedback.action,
            note=feedback.note
        )
        
        # Update org_grants status based on action
        status_map = {
            "saved": "saved",
            "dismissed": "dismissed",
            "applied": "applied",
            "won": "applied",  # Keep as applied, we'll track outcome separately
            "lost": "active"  # Revert to active
        }
        
        new_status = status_map.get(feedback.action, "active")
        
        _supabase.table("org_grants") \
            .update({"status": new_status}) \
            .eq("org_id", org_id) \
            .eq("grant_id", feedback.grant_id) \
            .execute()
        
        return {
            "status": "recorded",
            "org_id": org_id,
            "grant_id": feedback.grant_id,
            "action": feedback.action,
            "feedback_count": adaptive_agent.state["feedback_count"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[FEEDBACK] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accuracy")
async def get_scoring_accuracy(user_id: str = Depends(get_current_user)):
    """
    Get current scoring accuracy metrics for the org.
    
    Shows how well the adaptive scoring agent is performing.
    """
    org_id = await get_user_org_id(user_id)
    
    try:
        adaptive_agent = AdaptiveScoringAgent(org_id)
        accuracy = adaptive_agent.calculate_accuracy()
        
        return {
            "org_id": org_id,
            "current_version": adaptive_agent.state["current_version"],
            "total_scored": adaptive_agent.state["total_scored"],
            "feedback_count": adaptive_agent.state["feedback_count"],
            "accuracy": accuracy,
            "evolution_count": len(adaptive_agent.state.get("evolution_history", []))
        }
    except Exception as e:
        print(f"[FEEDBACK] Error getting accuracy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
