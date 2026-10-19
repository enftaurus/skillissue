from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.analytics.schemas import AnalyticsDashboardResponse
from backend.app.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics & Progress"])

@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def get_analytics_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await AnalyticsService.get_dashboard(db, current_user.id)
