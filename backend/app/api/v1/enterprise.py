from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_recruiter_user
from backend.app.core.rate_limit import rate_limit
from backend.app.enterprise.schemas import (
    CreatePipelineRequest, UpdatePipelineRequest, AssessmentPipelineResponse,
    CandidateInviteRequest, CandidateEntryRequest,
    CandidateAssessmentResponse, CandidateSubmitRoundRequest, PipelineLeaderboardResponse
)
from backend.app.enterprise.service import EnterpriseService

router = APIRouter(prefix="/enterprise", tags=["Enterprise & Campus Placement Exam"])

@router.post("/pipelines", response_model=AssessmentPipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment_pipeline(
    req: CreatePipelineRequest,
    current_user: User = Depends(get_current_recruiter_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Recruiter/TPO creates a customized multi-round assessment pipeline from a Job Description.
    """
    return await EnterpriseService.create_pipeline(db, current_user, req)

@router.get("/pipelines", response_model=List[AssessmentPipelineResponse])
async def list_assessment_pipelines(
    current_user: User = Depends(get_current_recruiter_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists assessment pipelines visible to the authenticated recruiter's tenant.
    """
    return await EnterpriseService.list_pipelines(db, current_user)

@router.get("/pipelines/{pipeline_id}", response_model=AssessmentPipelineResponse)
async def get_assessment_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_recruiter_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches pipeline details and round configuration.
    """
    return await EnterpriseService.get_pipeline_by_id(db, current_user, pipeline_id)

@router.put("/pipelines/{pipeline_id}", response_model=AssessmentPipelineResponse)
async def update_assessment_pipeline(
    pipeline_id: str,
    req: UpdatePipelineRequest,
    current_user: User = Depends(get_current_recruiter_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates pipeline details and round configuration within tenant boundary.
    """
    return await EnterpriseService.update_pipeline(db, current_user, pipeline_id, req)

@router.post("/pipelines/{pipeline_id}/invite", response_model=CandidateAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def invite_candidate(
    pipeline_id: str,
    req: CandidateInviteRequest,
    current_user: User = Depends(get_current_recruiter_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a unique candidate exam invitation link.
    """
    return await EnterpriseService.invite_candidate(db, current_user, pipeline_id, req)

@router.get("/pipelines/{pipeline_id}/leaderboard", response_model=PipelineLeaderboardResponse)
async def get_pipeline_leaderboard(
    pipeline_id: str,
    current_user: User = Depends(get_current_recruiter_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns ranked candidate leaderboard with composite scores and integrity signals.
    """
    return await EnterpriseService.get_pipeline_leaderboard(db, current_user, pipeline_id)

@router.get("/pipelines/{pipeline_id}/export")
async def export_pipeline_candidates(
    pipeline_id: str,
    current_user: User = Depends(get_current_recruiter_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Exports candidates and scores for an assessment pipeline within tenant boundary.
    """
    return await EnterpriseService.export_pipeline_candidates(db, current_user, pipeline_id)

# Candidate Public Assessment Endpoints (Token-Authenticated)
@router.get("/assessments/{token}", response_model=CandidateAssessmentResponse)
async def get_candidate_exam(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Candidate enters the multi-round assessment runner using their unique access token or general invite token.
    """
    return await EnterpriseService.get_candidate_exam_by_token(db, token)

@router.post(
    "/assessments/entry/{invite_token}",
    response_model=CandidateAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))]
)
async def enter_candidate_assessment(
    invite_token: str,
    req: CandidateEntryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Candidate enters their name and email at the invite link entry screen to start/resume assessment.
    """
    return await EnterpriseService.enter_assessment(db, invite_token, req)

@router.post("/assessments/{token}/submit-round", response_model=CandidateAssessmentResponse)
async def submit_candidate_round(
    token: str,
    req: CandidateSubmitRoundRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Candidate completes a round and transitions to the next round in the unified exam session.
    """
    return await EnterpriseService.submit_candidate_round(db, token, req)
