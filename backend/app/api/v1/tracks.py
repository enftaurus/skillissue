from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.tracks.schemas import (
    CompanyTrackSummary, CompanyTrackDetail, CompanyProblemDetail,
    SolveCompanyProblemRequest, SolveCompanyProblemResponse,
    PresetSimulationResponse
)
from backend.app.tracks.service import CompanyTrackService

router = APIRouter(prefix="/tracks", tags=["Company Career Tracks"])

@router.get("/simulations", response_model=List[PresetSimulationResponse])
async def list_preset_simulations(
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns full company hiring assessment simulations (Google SDE, Uber SDE, OpenAI AI Engineer).
    Features OA -> Take-Home Project -> Cross-Exam Interview.
    """
    return CompanyTrackService.get_all_simulations()

@router.get("/simulations/{sim_id}", response_model=PresetSimulationResponse)
async def get_preset_simulation(
    sim_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns details of a specific hiring assessment simulation.
    """
    return CompanyTrackService.get_simulation_by_id(sim_id)

@router.get("/companies", response_model=List[CompanyTrackSummary])
async def list_company_tracks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns curated company tracks across Gold, Silver, and Bronze mines.
    All companies feature 2-3 flagship problems unlocked on Day 1, with more unlocking via practice.
    """
    return await CompanyTrackService.get_all_tracks(db, current_user.id)

@router.get("/companies/{slug}", response_model=CompanyTrackDetail)
async def get_company_track_by_slug(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns specific company track details including community debrief insights and problem unlock states.
    """
    return await CompanyTrackService.get_track_by_slug(db, current_user.id, slug)

@router.get("/problems/{problem_id}", response_model=CompanyProblemDetail)
async def get_company_problem(
    problem_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns problem details with starter code and test cases if currently unlocked for user.
    """
    return await CompanyTrackService.get_problem_detail(db, current_user.id, problem_id)

@router.post("/problems/{problem_id}/solve", response_model=SolveCompanyProblemResponse)
async def solve_and_unlock_problem(
    problem_id: str,
    req: SolveCompanyProblemRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes code in isolated sandbox against test cases. If passed, unlocks the next locked question in this track.
    """
    return await CompanyTrackService.solve_and_unlock(
        db, current_user.id, problem_id, req.code, req.language
    )
