from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user, get_current_admin_user
from backend.app.analytics.schemas import (
    AnalyticsDashboardResponse, UserSkillResponse, FunnelTelemetryResponse, AdminAnalyticsResponse
)
from backend.app.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics & Progress"])

@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def get_analytics_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await AnalyticsService.get_dashboard(db, current_user.id)

@router.get("/skills", response_model=List[UserSkillResponse])
async def get_user_skills(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    skills = await AnalyticsService.get_skills(db, current_user.id)
    return [UserSkillResponse.model_validate(s) for s in skills]

@router.get("/funnel", response_model=FunnelTelemetryResponse)
async def get_funnel_telemetry(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns platform-wide activation funnel metrics, drop-off rates, and provider reliability signals.
    """
    return await AnalyticsService.get_funnel_telemetry(db)

@router.get("/admin/stats", response_model=AdminAnalyticsResponse)
async def get_admin_analytics_stats(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns admin tenant telemetry with strict isolation between Real Candidate Stats and Test/Sandbox Stats.
    """
    return await AnalyticsService.get_admin_analytics(db, limit=limit, offset=offset)

