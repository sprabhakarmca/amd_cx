from fastapi import APIRouter
from app.services.metrics import metrics_service

router = APIRouter(prefix="/api", tags=["observability"])


@router.get("/metrics")
async def get_metrics():
    return metrics_service.get_summary()


@router.get("/metrics/trends")
async def get_trends(days: int = 7):
    return metrics_service.get_trends(days=days)
