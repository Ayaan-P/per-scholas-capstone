"""Health check routes"""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])

# scheduler_service will be injected from main.py
scheduler_service = None


def set_scheduler_service(svc):
    """Allow main.py to inject the scheduler service reference"""
    global scheduler_service
    scheduler_service = svc


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "PerScholas Fundraising API",
        "scheduler_running": scheduler_service is not None
    }
