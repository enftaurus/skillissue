from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.interviews.schemas import (
    InterviewCreateDomain, InterviewCreateJd, InterviewMessageCreate,
    InterviewResponse, InterviewDetailResponse, InterviewMessageResponse,
    HintRequest, HintResponse
)
from backend.app.interviews.service import InterviewService
from backend.app.interviews.rubrics import get_rubric_for_category, RubricDimension
from backend.app.core.rate_limit import rate_limit

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post(
    "/domain",
    response_model=InterviewDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))]
)
async def create_domain_interview(
    data: InterviewCreateDomain,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await InterviewService.create_domain_interview(db, current_user.id, data)

@router.post(
    "/jd",
    response_model=InterviewDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))]
)
async def create_jd_interview(
    data: InterviewCreateJd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await InterviewService.create_jd_interview(db, current_user.id, data)

@router.get("", response_model=List[InterviewResponse])
async def list_interviews(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await InterviewService.list_interviews(db, current_user.id)

@router.get("/{interview_id}", response_model=InterviewDetailResponse)
async def get_interview(
    interview_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await InterviewService.get_interview(db, current_user.id, interview_id)

@router.post(
    "/{interview_id}/message",
    response_model=InterviewMessageResponse,
    dependencies=[Depends(rate_limit(max_requests=15, window_seconds=60))]
)
async def send_interview_message(
    interview_id: str,
    data: InterviewMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await InterviewService.send_message(db, current_user.id, interview_id, data.content)

@router.post(
    "/{interview_id}/hint",
    response_model=HintResponse,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))]
)
async def request_socratic_hint(
    interview_id: str,
    data: HintRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await InterviewService.request_hint(
        db=db,
        user_id=current_user.id,
        interview_id=interview_id,
        level=data.level,
        problem_id=data.problem_id,
        current_code=data.current_code,
    )

@router.post("/{interview_id}/end", response_model=InterviewResponse)
async def end_interview_session(
    interview_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await InterviewService.end_interview(db, current_user.id, interview_id)


@router.get("/rubrics/{category}", response_model=List[RubricDimension])
async def get_category_rubrics(category: str):
    return get_rubric_for_category(category)
