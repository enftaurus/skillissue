from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_active_user
from backend.app.database.models import User
from backend.app.database.session import get_db
from backend.app.reports import service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("")
async def list_reports(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Every past report for the signed-in user: interview evaluations, AI prompt analyses, comprehension, simulations."""
    return await service.list_reports(db, current_user.id)


@router.get("/projects/{submission_id}")
async def project_report(submission_id: str, current_user: User = Depends(get_current_active_user),
                         db: AsyncSession = Depends(get_db)):
    return await service.project_report(db, current_user.id, submission_id)
