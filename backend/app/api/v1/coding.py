from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.coding.schemas import (
    CodeRunRequest, CodeExecutionResponse, CodingSubmissionResponse,
    CodingProblemPublic, CodingLimitsResponse, DsaCoachRequest, DsaCoachResponse
)
from backend.app.coding.problems import list_problems, get_problem
from backend.app.coding.service import CodingService
from backend.app.coding.coach import DsaCoachService
from backend.app.core.errors import EntityNotFoundError
from backend.app.core.rate_limit import rate_limit
from backend.app.core.config import settings

router = APIRouter(prefix="/coding", tags=["Coding Sandbox"])

@router.get("/limits", response_model=CodingLimitsResponse)
async def get_coding_limits():
    """Return real platform limits and execution constraints."""
    return CodingLimitsResponse(
        memory_limit_mb=256,
        time_limit_seconds=3.0,
        max_output_bytes=1048576,
        runtime=settings.SANDBOX_RUNTIME,
        supported_languages=["python", "cpp", "java"]
    )

@router.get("/problems", response_model=List[CodingProblemPublic])
async def get_coding_problems(
    current_user: User = Depends(get_current_active_user)
):
    """List all available problems with public test cases only."""
    return [p.to_public() for p in list_problems()]

@router.get("/problems/{problem_id}", response_model=CodingProblemPublic)
async def get_coding_problem(
    problem_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve problem details without leaking hidden verification tests."""
    problem = get_problem(problem_id)
    if not problem:
        raise EntityNotFoundError("CodingProblem", problem_id)
    return problem.to_public()

@router.post(
    "/run",
    response_model=CodeExecutionResponse,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))]
)
async def run_code_sample_tests(
    data: CodeRunRequest,
    current_user: User = Depends(get_current_active_user),
):
    return await CodingService.run_sample_tests(data)

@router.post(
    "/submit",
    response_model=CodingSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=15, window_seconds=60))]
)
async def submit_code_solution(
    data: CodeRunRequest,
    interview_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    submission = await CodingService.submit_solution(
        db=db,
        user_id=current_user.id,
        data=data,
        interview_id=interview_id,
    )
    return submission

@router.get("/submissions", response_model=List[CodingSubmissionResponse])
async def list_submissions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await CodingService.list_user_submissions(db, current_user.id)

@router.post(
    "/problems/{problem_id}/coach",
    response_model=DsaCoachResponse,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))]
)
async def get_dsa_coach_hint(
    problem_id: str,
    data: DsaCoachRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    On-demand Socratic DSA coaching agent.
    Provides progressive hints without giving away the full solution.
    Invoked ONLY on explicit user request.
    """
    return await DsaCoachService.get_hint(db, current_user.id, problem_id, data)
