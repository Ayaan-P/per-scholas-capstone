"""
Workspace routes - Session-based agentic interactions
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from auth_service import get_current_user
from workspace_service import get_workspace_service
import os
from pathlib import Path
import uuid
from datetime import datetime

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
    
    if not _supabase_service_role_key or not _supabase_url:
        raise HTTPException(
            status_code=500, 
            detail="Server configuration error: Supabase credentials not set"
        )
    
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


class UpdateProfileRequest(BaseModel):
    """Request model for updating organization profile from agent"""
    name: Optional[str] = None
    mission: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    impact_metrics: Optional[Dict[str, Any]] = None
    programs: Optional[List[str]] = None
    target_demographics: Optional[List[str]] = None
    website_url: Optional[str] = None
    contact_email: Optional[str] = None
    annual_budget: Optional[int] = None
    staff_size: Optional[int] = None
    service_regions: Optional[List[str]] = None
    # Add any other fields the agent might want to update


@router.post("/update-profile-from-agent")
async def update_profile_from_agent(
    profile_data: UpdateProfileRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Allow agent to update organization profile in database with extracted info from conversation.
    This creates the 'magic moment' where the agent auto-fills the profile.
    """
    import httpx
    
    org_id = await get_user_org_id(user_id)
    
    # Build update payload (only include non-None fields)
    update_data = {k: v for k, v in profile_data.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Update database
    headers = {
        "Authorization": f"Bearer {_supabase_service_role_key}",
        "apikey": _supabase_service_role_key,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    with httpx.Client() as client:
        update_url = f"{_supabase_url}/rest/v1/organization_config?id=eq.{org_id}"
        response = client.patch(update_url, headers=headers, json=update_data)
    
    if response.status_code not in [200, 204]:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to update profile: {response.text}"
        )
    
    # Sync back to workspace
    ws = get_workspace_service()
    
    # Fetch updated config
    with httpx.Client() as client:
        config_url = f"{_supabase_url}/rest/v1/organization_config?select=*&id=eq.{org_id}"
        fetch_response = client.get(config_url, headers=headers)
    
    if fetch_response.status_code == 200:
        updated_config = fetch_response.json()
        if updated_config:
            ws.sync_profile_from_db(org_id, updated_config[0])
    
    return {
        "status": "success", 
        "message": "Profile updated from agent conversation",
        "updated_fields": list(update_data.keys())
    }


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


# ============================================
# Agent Chat (the main interaction point)
# ============================================

class ChatRequest(BaseModel):
    session_id: str
    message: str
    include_grants: bool = True  # Include grant context in agent's knowledge


class StartSessionResponse(BaseModel):
    session_id: str
    greeting: str
    has_profile: bool


@router.post("/chat/start")
async def start_chat_session(
    request: CreateSessionRequest,
    user_id: str = Depends(get_current_user)
):
    """Start a new chat session with the agent"""
    from session_service import get_session_service
    import uuid
    
    try:
        org_id = await get_user_org_id(user_id)
    except HTTPException as e:
        if e.status_code == 400 and "no organization" in str(e.detail).lower():
            # User hasn't completed onboarding - use user_id as temp org_id
            org_id = f"temp-{user_id}"
        else:
            raise
    
    session_svc = get_session_service(_supabase)
    
    result = await session_svc.start_session(org_id, request.session_id)
    
    return {
        "status": "success",
        "session_id": result["session_id"],
        "greeting": result["greeting"],
        "has_profile": result["has_profile"]
    }


@router.post("/chat")
async def chat_with_agent(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """Send a message to the agent and get a response"""
    from session_service import get_session_service
    
    try:
        org_id = await get_user_org_id(user_id)
    except HTTPException as e:
        if e.status_code == 400 and "no organization" in str(e.detail).lower():
            org_id = f"temp-{user_id}"
        else:
            raise
    session_svc = get_session_service(_supabase)
    
    result = await session_svc.chat(
        org_id=org_id,
        session_id=request.session_id,
        user_message=request.message,
        include_grants=request.include_grants
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "status": "success",
        "response": result["response"],
        "session_id": result["session_id"],
        "tokens_used": result.get("tokens_used"),
        "model": result.get("model")
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Upload a document to the organization's workspace.
    Supports: PDF, DOCX, TXT (max 10MB)
    """
    # Get org ID
    try:
        org_id = await get_user_org_id(user_id)
    except HTTPException as e:
        if e.status_code == 400 and "no organization" in str(e.detail).lower():
            org_id = f"temp-{user_id}"
        else:
            raise
    
    # Validate file type
    allowed_types = {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'text/plain': '.txt',
        'text/markdown': '.md'
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: PDF, DOCX, TXT, MD"
        )
    
    # Validate file size (10MB max)
    MAX_SIZE = 10 * 1024 * 1024
    file_content = await file.read()
    if len(file_content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size: 10MB"
        )
    
    # Create uploads directory
    uploads_dir = Path("uploads") / org_id
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = allowed_types[file.content_type]
    original_name = file.filename or f"document{file_ext}"
    safe_name = "".join(c if c.isalnum() or c in '.-_' else '_' for c in original_name)
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{unique_id}_{safe_name}"
    
    # Save file
    file_path = uploads_dir / filename
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Store metadata in database
    file_record = {
        "org_id": org_id,
        "file_id": unique_id,
        "filename": safe_name,
        "file_path": str(file_path),
        "file_type": file_ext[1:],  # Remove dot
        "file_size": len(file_content),
        "uploaded_by": user_id,
        "uploaded_at": datetime.now().isoformat()
    }
    
    try:
        _supabase.table("workspace_files").insert(file_record).execute()
    except Exception as e:
        # If DB insert fails, still return success (file is saved)
        print(f"Warning: Failed to log file upload to DB: {e}")
    
    return {
        "status": "success",
        "file": {
            "id": unique_id,
            "filename": safe_name,
            "size": len(file_content),
            "type": file_ext[1:],
            "uploaded_at": file_record["uploaded_at"]
        }
    }


@router.get("/uploads")
async def list_uploads(user_id: str = Depends(get_current_user)):
    """List all uploaded documents for the organization"""
    try:
        org_id = await get_user_org_id(user_id)
    except HTTPException as e:
        if e.status_code == 400 and "no organization" in str(e.detail).lower():
            org_id = f"temp-{user_id}"
        else:
            raise
    
    try:
        result = _supabase.table("workspace_files") \
            .select("*") \
            .eq("org_id", org_id) \
            .order("uploaded_at", desc=True) \
            .execute()
        
        return {
            "status": "success",
            "files": result.data
        }
    except Exception as e:
        # Fallback: read from filesystem
        uploads_dir = Path("uploads") / org_id
        if not uploads_dir.exists():
            return {"status": "success", "files": []}
        
        files = []
        for f in uploads_dir.iterdir():
            if f.is_file():
                stat = f.stat()
                files.append({
                    "filename": f.name,
                    "size": stat.st_size,
                    "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return {"status": "success", "files": files}
