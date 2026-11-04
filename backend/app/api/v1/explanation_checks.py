"""FastAPI router for Explanation Check (cross-examination follow-up) feature."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.database.models import User, CandidateAssessment
from backend.app.core.errors import AuthenticationError
from backend.app.integrity.dependencies import get_integrity_actor
from backend.app.integrity.schemas import (
    CreateExplanationCheckRequest,
    SubmitAnswersRequest,
)
from backend.app.integrity.explanation_service import ExplanationService

router = APIRouter(prefix="/explanation-checks", tags=["Explanation Checks"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_explanation_check(
    req: CreateExplanationCheckRequest,
    actor: tuple = Depends(get_integrity_actor),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Initiate explanation check on a submitted code solution.

    Loads code securely server-side (never from request body), runs triviality gate,
    generates grounded questions, and returns them to the candidate without model rationale.
    """
    user, ca = actor
    if not user and not ca and not req.candidate_assessment_id:
        raise AuthenticationError("Authentication required (Bearer token or Candidate Assessment access)")

    check = await ExplanationService.create_explanation_check(
        req=req,
        db=db,
        current_user=user,
        candidate_assessment=ca,
    )

    return {
        "id": check.id,
        "round_key": check.round_key,
        "submission_ref": check.submission_ref,
        "mode": check.mode,
        "status": check.status,
        "discriminative_power": check.discriminative_power,
        "questions": check.questions,
        "time_limit_per_question": 90,
    }


@router.post("/{check_id}/answers", status_code=status.HTTP_200_OK)
async def submit_explanation_answers(
    check_id: str,
    req: SubmitAnswersRequest,
    actor: tuple = Depends(get_integrity_actor),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Submit candidate answers to explanation check.

    Enforces single submission and time limits. Triggers server-side LLM judging and
    review flag generation in assessment mode. Never alters composite score or ranking.
    """
    user, ca = actor
    check = await ExplanationService.submit_answers(
        check_id=check_id,
        req=req,
        db=db,
        current_user=user,
        candidate_assessment=ca,
    )

    # Return safe candidate response
    if check.mode == "assessment":
        return {
            "id": check.id,
            "status": "submitted",
            "message": "Thanks, your answers are submitted.",
        }
    else:
        coaching = None
        if check.evaluation:
            coaching = {
                "what_went_well": check.evaluation.get("coaching_what_went_well", []),
                "what_to_revisit": check.evaluation.get("coaching_what_to_revisit", []),
            }
        return {
            "id": check.id,
            "status": check.status,
            "coaching": coaching,
            "message": "Coaching feedback generated.",
        }


@router.get("/{check_id}", status_code=status.HTTP_200_OK)
async def get_explanation_check(
    check_id: str,
    actor: tuple = Depends(get_integrity_actor),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Fetch explanation check.

    Candidate sees coaching in practice mode and only 'submitted' in assessment mode.
    Recruiters in the same tenant see full evaluation. Enforces tenant isolation.
    """
    user, ca = actor
    if not user and not ca:
        raise AuthenticationError("Authentication required")

    return await ExplanationService.get_explanation_check(
        check_id=check_id,
        db=db,
        current_user=user,
        candidate_assessment=ca,
    )
