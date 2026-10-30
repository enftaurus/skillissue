from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.projects.schemas import (
    ProjectSummary,
    ProjectDetail,
    ProjectRunTestsRequest,
    ProjectTestRunResponse,
    ProjectCopilotRequest,
    ProjectCopilotResponse,
    ProjectPromptAnalysisResponse,
    ProjectSubmissionRequest,
    ProjectSubmissionResponse,
)
from backend.app.projects.repository import list_projects, get_project
from backend.app.projects.service import ProjectService
from backend.app.projects.copilot import ProjectCopilotService
from backend.app.projects.prompt_evaluator import evaluate_candidate_prompts
from backend.app.core.errors import EntityNotFoundError
from backend.app.core.rate_limit import rate_limit

router = APIRouter(prefix="/projects", tags=["AI Coding Projects"])

@router.get("", response_model=List[ProjectSummary])
async def get_projects(
    current_user: User = Depends(get_current_active_user)
):
    """List all available AI-assisted work simulation coding projects."""
    return list_projects()

@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project_details(
    project_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve full project details and virtual repository files."""
    project = get_project(project_id)
    if not project:
        raise EntityNotFoundError("ProjectChallenge", project_id)
    return project

@router.post(
    "/{project_id}/run-tests",
    response_model=ProjectTestRunResponse,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))]
)
async def run_project_tests(
    project_id: str,
    data: ProjectRunTestsRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Run automated CI/CD unit & integration tests inside an isolated sandbox."""
    return ProjectService.run_tests_in_sandbox(project_id, data.files)

@router.post(
    "/{project_id}/copilot",
    response_model=ProjectCopilotResponse,
    dependencies=[Depends(rate_limit(max_requests=25, window_seconds=60))]
)
async def ask_project_copilot(
    project_id: str,
    data: ProjectCopilotRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    On-demand read-only AI pair programming assistant.
    Provides architectural guidance and hints without directly modifying repository files.
    """
    return await ProjectCopilotService.ask_copilot(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
        data=data,
    )

@router.post(
    "/{project_id}/evaluate-prompts",
    response_model=ProjectPromptAnalysisResponse,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))]
)
async def evaluate_prompts(
    project_id: str,
    data: ProjectSubmissionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Analyze candidate's prompt engineering quality, detect amateurish prompts, and suggest senior rewrites."""
    return evaluate_candidate_prompts(
        project_id=project_id,
        conversation_history=data.conversation_history,
        time_spent_seconds=data.time_spent_seconds,
    )

@router.post(
    "/{project_id}/submit",
    response_model=ProjectSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))]
)
async def submit_project(
    project_id: str,
    data: ProjectSubmissionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit the project challenge, run CI/CD tests, analyze prompt quality, and persist submission."""
    return await ProjectService.submit_project(
        db=db,
        user_id=current_user.id,
        project_id=project_id,
        data=data,
    )
