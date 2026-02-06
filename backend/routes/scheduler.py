"""Scheduler routes for controlling scraping jobs"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from auth_service import get_current_user

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])

# These will be injected from main.py
scheduler_service = None
supabase = None


def set_dependencies(svc, db):
    """Allow main.py to inject dependencies"""
    global scheduler_service, supabase
    scheduler_service = svc
    supabase = db


class SchedulerSettingsRequest(BaseModel):
    scheduler_frequency: str  # 'daily', 'weekly', 'biweekly', 'monthly'
    selected_states: Optional[List[str]] = None
    selected_cities: Optional[List[str]] = None


class SchedulerSettingsResponse(BaseModel):
    id: str
    scheduler_frequency: str
    selected_states: List[str]
    selected_cities: List[str]
    created_at: str
    updated_at: str


# Default states and cities for new settings
DEFAULT_STATES = ["CA", "NY", "TX", "GA", "MD", "MA", "IL", "CO", "MI", "IN", "MO", "PA", "NC", "FL", "AZ", "WA", "VA", "OH", "TN"]
DEFAULT_CITIES = [
    "Los Angeles/San Francisco", "New York/Newark", "Dallas/Houston", "Atlanta", 
    "Baltimore", "Boston", "Chicago", "Denver", "Detroit", "Indianapolis", 
    "Kansas City/St. Louis", "Philadelphia/Pittsburgh", "Charlotte/Raleigh", 
    "Orlando/Tampa/Miami", "Phoenix", "Seattle", "Washington DC/Virginia", 
    "Cincinnati/Columbus/Cleveland", "Nashville"
]


@router.get("/settings")
async def get_scheduler_settings(user_id: str = Depends(get_current_user)):
    """Get current scheduler settings (requires authentication)"""
    try:
        result = supabase.table("scheduler_settings").select("*").limit(1).execute()

        if result.data and len(result.data) > 0:
            settings = result.data[0]
            return {
                "id": settings.get("id"),
                "scheduler_frequency": settings.get("scheduler_frequency", "weekly"),
                "selected_states": settings.get("selected_states", []),
                "selected_cities": settings.get("selected_cities", []),
                "created_at": settings.get("created_at"),
                "updated_at": settings.get("updated_at")
            }
        else:
            # Return default settings if none exist
            return {
                "id": None,
                "scheduler_frequency": "weekly",
                "selected_states": DEFAULT_STATES,
                "selected_cities": DEFAULT_CITIES,
                "created_at": None,
                "updated_at": None
            }
    except Exception as e:
        print(f"[SCHEDULER SETTINGS] Error fetching settings: {e}")
        # Return default settings on error
        return {
            "id": None,
            "scheduler_frequency": "weekly",
            "selected_states": DEFAULT_STATES,
            "selected_cities": DEFAULT_CITIES,
            "created_at": None,
            "updated_at": None
        }


@router.post("/settings")
async def save_scheduler_settings(settings: SchedulerSettingsRequest, user_id: str = Depends(get_current_user)):
    """Save or update scheduler settings and reload scheduler (requires authentication)"""
    try:
        # Check if settings already exist
        result = supabase.table("scheduler_settings").select("id").limit(1).execute()

        settings_data = {
            "scheduler_frequency": settings.scheduler_frequency,
        }

        # Only update states/cities if they were provided
        if settings.selected_states:
            settings_data["selected_states"] = settings.selected_states
        if settings.selected_cities:
            settings_data["selected_cities"] = settings.selected_cities

        if result.data and len(result.data) > 0:
            # Update existing settings
            existing_id = result.data[0]["id"]
            update_result = supabase.table("scheduler_settings").update(settings_data).eq("id", existing_id).execute()

            if update_result.data:
                saved_settings = update_result.data[0]

                # Reload scheduler settings immediately (no need to restart)
                if scheduler_service:
                    reload_success = await scheduler_service.reload_scheduler_settings()
                    print(f"[SCHEDULER SETTINGS] Scheduler reload: {'success' if reload_success else 'failed'}")

                return {
                    "status": "updated",
                    "id": saved_settings.get("id"),
                    "scheduler_frequency": saved_settings.get("scheduler_frequency"),
                    "selected_states": saved_settings.get("selected_states", []),
                    "selected_cities": saved_settings.get("selected_cities", []),
                    "updated_at": saved_settings.get("updated_at"),
                    "scheduler_reloaded": True
                }
        else:
            # Create new settings
            insert_result = supabase.table("scheduler_settings").insert(settings_data).execute()

            if insert_result.data:
                saved_settings = insert_result.data[0]

                # Reload scheduler settings immediately (no need to restart)
                if scheduler_service:
                    reload_success = await scheduler_service.reload_scheduler_settings()
                    print(f"[SCHEDULER SETTINGS] Scheduler reload: {'success' if reload_success else 'failed'}")

                return {
                    "status": "created",
                    "id": saved_settings.get("id"),
                    "scheduler_frequency": saved_settings.get("scheduler_frequency"),
                    "selected_states": saved_settings.get("selected_states", []),
                    "selected_cities": saved_settings.get("selected_cities", []),
                    "created_at": saved_settings.get("created_at"),
                    "scheduler_reloaded": True
                }

        raise Exception("Failed to save settings")
    except Exception as e:
        print(f"[SCHEDULER SETTINGS] Error saving settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save scheduler settings: {str(e)}")


@router.get("/status")
async def get_scheduler_status(user_id: str = Depends(get_current_user)):
    """Get status of scheduled scraping jobs (requires authentication)"""
    if not scheduler_service:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    try:
        jobs = scheduler_service.get_job_status()
        scheduled_jobs = []

        # Get info about scheduled jobs
        for job in scheduler_service.scheduler.get_jobs():
            scheduled_jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })

        return {
            "scheduler_running": True,
            "recent_jobs": jobs,
            "scheduled_jobs": scheduled_jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@router.post("/run/{job_name}")
async def run_scheduler_job(job_name: str, user_id: str = Depends(get_current_user)):
    """Manually trigger a scheduled scraping job (requires authentication)"""
    if not scheduler_service:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    try:
        await scheduler_service.run_job_now(job_name)
        return {
            "status": "started",
            "job_name": job_name,
            "message": f"Job '{job_name}' triggered successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run job: {str(e)}")
