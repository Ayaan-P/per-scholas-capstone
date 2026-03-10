"""
Processing routes - Trigger grant qualification and scoring
"""

import logging
import re
import asyncio
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from auth_service import get_current_user
import subprocess
import os
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)

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
        
        logger.info(" Qualification agent for org {org_id}")
        logger.info(" stdout: {result.stdout}")
        if result.stderr:
            logger.info(" stderr: {result.stderr}")
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        logger.info(" Timeout running qualification agent for org {org_id}")
        return {
            "success": False,
            "error": "Processing timeout (>5 min)"
        }
    except Exception as e:
        logger.info(" Error: {e}")
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
        logger.info(" Error checking status: {e}")
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
            
            logger.info(" Manual trigger completed")
            logger.info(" stdout: {result.stdout}")
            if result.stderr:
                logger.info(" stderr: {result.stderr}")
        except Exception as e:
            logger.info(" Error: {e}")
    
    background_tasks.add_task(run_brief_generation)
    
    return {
        "status": "processing",
        "message": "Brief generation started in background",
        "org_id": org_id
    }


# ============================================================================
# URL Validation
# ============================================================================

# Patterns for generic/useless URLs
GENERIC_URL_PATTERNS = [
    r'^https?://[^/]+/?$',  # Just domain, no path (e.g., https://example.com/)
    r'fordfoundation\.org/grants/?$',
    r'macfound\.org/grants/?$',
    r'gatesfoundation\.org/?',
    r'rockefellerfoundation\.org/grants/?$',
    r'grants\.gov/?$',  # Just grants.gov without specific grant
    r'microsoft\.com/.*nonprofits/?$',
    r'salesforce\.(org|com)/.*grant-program/?$',
]

GENERIC_URL_REGEX = re.compile('|'.join(GENERIC_URL_PATTERNS), re.IGNORECASE)


def is_generic_url(url: str) -> bool:
    """Check if URL is a generic landing page, not a specific grant"""
    if not url:
        return True
    return bool(GENERIC_URL_REGEX.search(url))


async def check_url_accessible(url: str, timeout: float = 10.0) -> dict:
    """
    Check if a URL is accessible and returns useful content.
    Returns: {accessible: bool, status_code: int, error: str|None, is_generic: bool}
    """
    if not url:
        return {"accessible": False, "status_code": 0, "error": "No URL", "is_generic": True}
    
    if is_generic_url(url):
        return {"accessible": True, "status_code": 0, "error": "Generic URL", "is_generic": True}
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.head(url)
            
            # If HEAD fails, try GET
            if response.status_code >= 400:
                response = await client.get(url)
            
            return {
                "accessible": response.status_code < 400,
                "status_code": response.status_code,
                "error": None if response.status_code < 400 else f"HTTP {response.status_code}",
                "is_generic": False
            }
    except httpx.TimeoutException:
        return {"accessible": False, "status_code": 0, "error": "Timeout", "is_generic": False}
    except Exception as e:
        return {"accessible": False, "status_code": 0, "error": str(e)[:100], "is_generic": False}


class ValidateUrlsRequest(BaseModel):
    limit: int = 100
    fix: bool = False  # If True, dismiss grants with bad URLs


@router.post("/validate-urls")
async def validate_grant_urls(
    request: ValidateUrlsRequest,
    background_tasks: BackgroundTasks
):
    """
    Validate grant URLs and optionally dismiss grants with broken/generic URLs.
    
    This checks:
    - Null/empty URLs
    - Generic landing pages (not specific grants)
    - 404s and other HTTP errors
    
    If fix=True, marks invalid grants as 'dismissed' with reason.
    """
    if not _supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    async def run_validation():
        # Get active grants
        result = _supabase.table("scraped_grants") \
            .select("id,title,application_url,source") \
            .eq("status", "active") \
            .limit(request.limit) \
            .execute()
        
        grants = result.data or []
        
        results = {
            "total": len(grants),
            "valid": 0,
            "null_url": 0,
            "generic_url": 0,
            "broken_url": 0,
            "dismissed": [],
            "errors": []
        }
        
        # Check URLs in parallel (batches of 10)
        async def check_grant(grant):
            url = grant.get("application_url")
            grant_id = grant.get("id")
            
            if not url:
                results["null_url"] += 1
                return {"id": grant_id, "status": "null_url", "url": None}
            
            check = await check_url_accessible(url)
            
            if check["is_generic"]:
                results["generic_url"] += 1
                return {"id": grant_id, "status": "generic_url", "url": url}
            elif not check["accessible"]:
                results["broken_url"] += 1
                return {"id": grant_id, "status": "broken_url", "url": url, "error": check["error"]}
            else:
                results["valid"] += 1
                return {"id": grant_id, "status": "valid", "url": url}
        
        # Process in batches
        batch_size = 10
        invalid_grants = []
        
        for i in range(0, len(grants), batch_size):
            batch = grants[i:i+batch_size]
            batch_results = await asyncio.gather(*[check_grant(g) for g in batch])
            
            for r in batch_results:
                if r["status"] != "valid":
                    invalid_grants.append(r)
        
        # Dismiss invalid grants if fix=True
        if request.fix and invalid_grants:
            for inv in invalid_grants:
                try:
                    _supabase.table("scraped_grants") \
                        .update({
                            "status": "dismissed",
                            "requirements": [f"Auto-dismissed: {inv['status']} - {inv.get('error', inv.get('url', 'no url'))}"]
                        }) \
                        .eq("id", inv["id"]) \
                        .execute()
                    results["dismissed"].append(inv["id"])
                except Exception as e:
                    results["errors"].append({"id": inv["id"], "error": str(e)})
        
        logger.info(f"URL validation complete: {results}")
        return results
    
    # Run in background for large batches
    if request.limit > 50:
        background_tasks.add_task(run_validation)
        return {
            "status": "processing",
            "message": f"Validating {request.limit} grants in background"
        }
    else:
        return await run_validation()


@router.get("/url-health")
async def get_url_health():
    """
    Quick health check of URL quality across all active grants.
    Returns counts by category without actually checking URLs.
    """
    if not _supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Get all active grants
    result = _supabase.table("scraped_grants") \
        .select("application_url,source") \
        .eq("status", "active") \
        .execute()
    
    grants = result.data or []
    
    stats = {
        "total": len(grants),
        "null_urls": 0,
        "generic_urls": 0,
        "specific_urls": 0,
        "by_source": {}
    }
    
    for g in grants:
        url = g.get("application_url")
        source = g.get("source", "unknown")
        
        if source not in stats["by_source"]:
            stats["by_source"][source] = {"total": 0, "null": 0, "generic": 0, "specific": 0}
        
        stats["by_source"][source]["total"] += 1
        
        if not url:
            stats["null_urls"] += 1
            stats["by_source"][source]["null"] += 1
        elif is_generic_url(url):
            stats["generic_urls"] += 1
            stats["by_source"][source]["generic"] += 1
        else:
            stats["specific_urls"] += 1
            stats["by_source"][source]["specific"] += 1
    
    stats["health_score"] = round(stats["specific_urls"] / max(stats["total"], 1) * 100, 1)
    
    return stats
