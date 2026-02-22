"""Health check routes"""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])

# scheduler_service will be injected from main.py
scheduler_service = None
brief_scheduler = None


def set_scheduler_service(svc):
    """Allow main.py to inject the scheduler service reference"""
    global scheduler_service
    scheduler_service = svc


def set_brief_scheduler(svc):
    """Allow main.py to inject the brief scheduler reference"""
    global brief_scheduler
    brief_scheduler = svc


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "FundFish API",
        # Main scraping scheduler intentionally disabled — moved to Hetzner librarian agent
        "scraper_location": "hetzner",
        "local_scheduler_running": scheduler_service is not None,
        "brief_scheduler_running": brief_scheduler is not None and brief_scheduler.running
    }
