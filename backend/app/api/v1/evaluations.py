from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.evaluations.schemas import (
    SelfEvaluationCreate, SelfEvaluationResponse, EvaluationResponse, EvaluationComparisonResponse,
    RetestInitiateRequest, RetestSessionResponse
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

@router.post("/{evaluation_id}/retest", response_model=RetestSessionResponse, status_code=status.HTTP_201_CREATED)
async def initiate_weakness_retest(
    evaluation_id: str,
    req: RetestInitiateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Provisions a focused 3-question adaptive retest interview on an identified weakness topic.
    """
    return await EvaluationService.initiate_retest(
        db, current_user.id, evaluation_id, req.weakness_topic, req.baseline_score
    )

@router.get("/{evaluation_id}/retests", response_model=List[RetestSessionResponse])
async def list_evaluation_retests(
    evaluation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns retest sessions and delta progress records for an evaluation.
    """
    return await EvaluationService.get_retests_for_evaluation(db, current_user.id, evaluation_id)

@router.post("/retests/{retest_id}/complete", response_model=RetestSessionResponse)
async def complete_retest_and_calculate_delta(
    retest_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculates the Before vs After Delta Score and verified improvements for a completed retest interview.
    """
    return await EvaluationService.complete_retest_and_calculate_delta(db, current_user.id, retest_id)
