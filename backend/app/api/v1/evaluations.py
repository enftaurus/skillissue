from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.evaluations.schemas import (
    SelfEvaluationCreate, SelfEvaluationResponse, EvaluationResponse, EvaluationComparisonResponse
)
from backend.app.evaluations.service import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])

@router.post("/self", response_model=SelfEvaluationResponse, status_code=status.HTTP_201_CREATED)
async def submit_self_evaluation(
    data: SelfEvaluationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await EvaluationService.save_self_evaluation(db, current_user.id, data)

@router.post("/{interview_id}/generate", response_model=EvaluationResponse)
async def generate_ai_evaluation(
    interview_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await EvaluationService.generate_ai_evaluation(db, current_user.id, interview_id)

@router.get("/{interview_id}", response_model=EvaluationResponse)
async def get_evaluation(
    interview_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await EvaluationService.get_evaluation(db, current_user.id, interview_id)

@router.get("/{interview_id}/comparison", response_model=EvaluationComparisonResponse)
async def get_self_vs_ai_comparison(
    interview_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await EvaluationService.get_comparison(db, current_user.id, interview_id)
