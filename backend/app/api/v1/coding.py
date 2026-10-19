from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.coding.schemas import (
    CodeRunRequest, CodeExecutionResponse, CodingSubmissionResponse
)
from backend.app.coding.problems import list_problems, get_problem, CodingProblem
from backend.app.coding.service import CodingService
from backend.app.core.errors import EntityNotFoundError

router = APIRouter(prefix="/coding", tags=["Coding Sandbox"])

@router.get("/problems", response_model=List[CodingProblem])
async def get_coding_problems():
    return list_problems()

@router.get("/problems/{problem_id}", response_model=CodingProblem)
async def get_coding_problem(problem_id: str):
    problem = get_problem(problem_id)
    if not problem:
        raise EntityNotFoundError("CodingProblem", problem_id)
    return problem

@router.post("/run", response_model=CodeExecutionResponse)
async def run_code_sample_tests(
    data: CodeRunRequest,
    current_user: User = Depends(get_current_active_user),
):
    return await CodingService.run_sample_tests(data)

@router.post("/submit", response_model=CodingSubmissionResponse, status_code=status.HTTP_201_CREATED)
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
