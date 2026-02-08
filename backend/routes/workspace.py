"""
Workspace routes - Session-based agentic interactions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from auth_service import get_current_user
from workspace_service import get_workspace_service

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

# Module-level dependencies
_supabase = None
_supabase_url = None
_supabase_service_role_key = None


def set_dependencies(supabase, supabase_url: str, supabase_service_role_key: str):
    """Set dependencies from main app"""
    global _supabase, _supabase_url, _supabase_service_role_key
    _supabase = supabase
    _supabase_url = supabase_url
    _supabase_service_role_key = supabase_service_role_key


# ============================================
# Pydantic Models
# ============================================

class SessionMessage(BaseModel):
    role: str  # "user" or "agent"
    content: str


class CreateSessionRequest(BaseModel):
    session_id: Optional[str] = None


class UpdateStyleRequest(BaseModel):
    content: str


class AddDecisionRequest(BaseModel):
    decision: str


class SaveGrantRequest(BaseModel):
    grant_id: str
    grant_data: Dict[str, Any]


# ============================================
# Helper Functions
# ============================================

async def get_user_org_id(user_id: str) -> str:
    """Get organization ID for authenticated user"""
    import httpx
    
    headers = {
        "Authorization": f"Bearer {_supabase_service_role_key}",
        "apikey": _supabase_service_role_key,
    }
    
    with httpx.Client() as client:
        user_url = f"{_supabase_url}/rest/v1/users?select=organization_id&id=eq.{user_id}"
        response = client.get(user_url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = response.json()
    if not data or not data[0].get("organization_id"):
        raise HTTPException(status_code=400, detail="User has no organization")
    
    return data[0]["organization_id"]


# ============================================
# Workspace Management
# ============================================

@router.post("/init")
async def init_workspace(user_id: str = Depends(get_current_user)):
    """Initialize workspace for user's organization"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    result = ws.init_workspace(org_id)
    return {"status": "success", **result}


@router.get("/status")
async def workspace_status(user_id: str = Depends(get_current_user)):
    """Check if workspace exists and get basic info"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    exists = ws.workspace_exists(org_id)
    
    if not exists:
        return {"exists": False, "org_id": org_id}
    
    context = ws.get_agent_context(org_id)
    sessions = ws.list_sessions(org_id, limit=5)
    
    return {
        "exists": True,
        "org_id": org_id,
        "has_profile": "profile" in context,
        "has_style": "style" in context,
        "recent_sessions": len(sessions),
        "sessions": sessions
    }


@router.post("/sync-profile")
async def sync_profile(user_id: str = Depends(get_current_user)):
    """Sync organization profile from database to workspace"""
    import httpx
    
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    # Fetch org config from database
    headers = {
        "Authorization": f"Bearer {_supabase_service_role_key}",
        "apikey": _supabase_service_role_key,
    }
    
    with httpx.Client() as client:
        config_url = f"{_supabase_url}/rest/v1/organization_config?select=*&id=eq.{org_id}"
        response = client.get(config_url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch organization config")
    
    data = response.json()
    if not data:
        raise HTTPException(status_code=404, detail="Organization config not found")
    
    org_config = data[0]
    ws.sync_profile_from_db(org_id, org_config)
    
    return {"status": "success", "message": "Profile synced to workspace"}


# ============================================
# Session Management
# ============================================

@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    user_id: str = Depends(get_current_user)
):
    """Create a new conversation session"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    result = ws.create_session(org_id, request.session_id)
    return {"status": "success", **result}


@router.get("/sessions")
async def list_sessions(
    limit: int = 10,
    user_id: str = Depends(get_current_user)
):
    """List recent sessions"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    sessions = ws.list_sessions(org_id, limit)
    return {"sessions": sessions, "count": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get session history"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    history = ws.get_session_history(org_id, session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"session_id": session_id, "history": history}


@router.post("/sessions/{session_id}/messages")
async def add_message(
    session_id: str,
    message: SessionMessage,
    user_id: str = Depends(get_current_user)
):
    """Add a message to session history"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    success = ws.append_to_session(org_id, session_id, message.role, message.content)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "success"}


# ============================================
# Agent Context
# ============================================

@router.get("/context")
async def get_context(user_id: str = Depends(get_current_user)):
    """Get all context for agent consumption"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    # Ensure workspace exists
    ws.init_workspace(org_id)
    
    context = ws.get_agent_context(org_id)
    return {"org_id": org_id, "context": context}


@router.get("/style")
async def get_style(user_id: str = Depends(get_current_user)):
    """Get writing style guide"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    context = ws.get_agent_context(org_id)
    return {"style": context.get("style", "")}


@router.put("/style")
async def update_style(
    request: UpdateStyleRequest,
    user_id: str = Depends(get_current_user)
):
    """Update writing style guide"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    ws._ensure_workspace(org_id)
    style_path = ws._org_path(org_id) / "STYLE.md"
    style_path.write_text(request.content)
    
    return {"status": "success", "message": "Style guide updated"}


# ============================================
# Decisions
# ============================================

@router.post("/decisions")
async def add_decision(
    request: AddDecisionRequest,
    user_id: str = Depends(get_current_user)
):
    """Add a decision to memory"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    ws.update_decisions(org_id, request.decision)
    return {"status": "success", "message": "Decision recorded"}


# ============================================
# Grant Tracking
# ============================================

@router.post("/grants/save")
async def save_grant(
    request: SaveGrantRequest,
    user_id: str = Depends(get_current_user)
):
    """Save a grant to workspace"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    ws.save_grant(org_id, request.grant_id, request.grant_data)
    return {"status": "success", "grant_id": request.grant_id}


@router.get("/grants/saved")
async def get_saved_grants(user_id: str = Depends(get_current_user)):
    """Get all saved grants"""
    org_id = await get_user_org_id(user_id)
    ws = get_workspace_service()
    
    grants = ws.get_saved_grants(org_id)
    return {"grants": grants, "count": len(grants)}
