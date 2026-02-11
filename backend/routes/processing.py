"""
Processing routes - Trigger grant qualification and scoring
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from auth_service import get_current_user
import subprocess
import os
from pathlib import Path

router = APIRouter(prefix="/api/processing", tags=["processing"])

# Module-level dependencies
_supabase = None

def set_dependencies(supabase):
    """Set dependencies from main app"""
    global _supabase
    _supabase = supabase


class ProcessGrantsRequest(BaseModel):
    org_id: Optional[str] = None
    since_hours: int = 720  # Default: last 30 days
    force: bool = False
    dry_run: bool = False


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


def run_qualification_agent(org_id: str, since_hours: int = 720, force: bool = False, dry_run: bool = False):
    """Run the qualification agent in the background"""
    backend_dir = Path(__file__).parent.parent
    script_path = backend_dir / "jobs" / "process_grants.py"
    
    cmd = [
        "python3",
        str(script_path),
        "--org-id", str(org_id),
        "--since-hours", str(since_hours)
    ]
    
    if force:
        cmd.append("--force")
    if dry_run:
        cmd.append("--dry-run")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout
        )
        
        print(f"[PROCESSING] Qualification agent for org {org_id}")
        print(f"[PROCESSING] stdout: {result.stdout}")
        if result.stderr:
            print(f"[PROCESSING] stderr: {result.stderr}")
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        print(f"[PROCESSING] Timeout running qualification agent for org {org_id}")
        return {
            "success": False,
            "error": "Processing timeout (>5 min)"
        }
    except Exception as e:
        print(f"[PROCESSING] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/qualify-grants")
async def qualify_grants(
    request: ProcessGrantsRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Trigger grant qualification for the user's organization.
    
    This runs the qualification agent which:
    - Reads new grants from scraped_grants
    - Scores them 0-100 based on org fit
    - Writes analysis to org_grants table
    """
    org_id = await get_user_org_id(user_id)
    
    # Run in background so request doesn't time out
    background_tasks.add_task(
        run_qualification_agent,
        org_id=org_id,
        since_hours=request.since_hours,
        force=request.force,
        dry_run=request.dry_run
    )
    
    return {
        "status": "processing",
        "message": "Qualification agent started in background",
        "org_id": org_id
    }


@router.get("/status")
async def processing_status(user_id: str = Depends(get_current_user)):
    """Check if org has scored grants (simple health check)"""
    org_id = await get_user_org_id(user_id)
    
    if not _supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Count org_grants for this org
        result = _supabase.table("org_grants") \
            .select("id", count="exact") \
            .eq("org_id", org_id) \
            .execute()
        
        return {
            "org_id": org_id,
            "scored_grants_count": result.count or 0,
            "has_scores": (result.count or 0) > 0
        }
    except Exception as e:
        print(f"[PROCESSING] Error checking status: {e}")
        return {
            "org_id": org_id,
            "scored_grants_count": 0,
            "has_scores": False,
            "error": str(e)
        }


@router.post("/generate-brief")
async def generate_brief(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Manually trigger morning brief generation for the user's org.
    
    Useful for testing. In production, this runs via cron at 8am daily.
    """
    org_id = await get_user_org_id(user_id)
    
    def run_brief_generation():
        """Run the brief generation script"""
        backend_dir = Path(__file__).parent.parent
        script_path = backend_dir / "jobs" / "generate_briefs.py"
        
        try:
            result = subprocess.run(
                ["python3", str(script_path)],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            print(f"[BRIEF] Manual trigger completed")
            print(f"[BRIEF] stdout: {result.stdout}")
            if result.stderr:
                print(f"[BRIEF] stderr: {result.stderr}")
        except Exception as e:
            print(f"[BRIEF] Error: {e}")
    
    background_tasks.add_task(run_brief_generation)
    
    return {
        "status": "processing",
        "message": "Brief generation started in background",
        "org_id": org_id
    }
