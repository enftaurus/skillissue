"""FastAPI router for Monaco editor telemetry ingestion and recruiter replay."""

from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.core.errors import AuthenticationError
from backend.app.auth.dependencies import get_current_user, get_current_admin_user
from backend.app.integrity.dependencies import get_integrity_actor
from backend.app.integrity.schemas import (
    EditorTelemetryBatchRequest,
    EditorTelemetryReplayResponse,
)
from backend.app.integrity.telemetry_service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["Editor Telemetry"])


@router.post("/editor", status_code=status.HTTP_200_OK)
async def ingest_editor_telemetry(
    req: EditorTelemetryBatchRequest,
    actor: tuple = Depends(get_integrity_actor),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Ingest editor telemetry batch from Monaco editor component.

    Requires valid candidate access token or session. Verifies sequence monotonicity,
    caps batch sizes, and stores deltas for replay analysis.
    """
    user, ca = actor
    if not ca:
        raise AuthenticationError("Valid candidate assessment session token required")

    return await TelemetryService.ingest_batch(
        req=req,
        candidate_assessment=ca,
        db=db,
    )


@router.get("/editor/{candidate_assessment_id}/{round_key}", response_model=EditorTelemetryReplayResponse)
async def get_editor_replay(
    candidate_assessment_id: str,
    round_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EditorTelemetryReplayResponse:
    """Fetch Monaco editor replay timeline, activity density, and integrity flags.

    Accessible only to recruiters in the same tenant and administrators. Enforces tenant isolation.
    """
    return await TelemetryService.get_replay_data(
        candidate_assessment_id=candidate_assessment_id,
        round_key=round_key,
        current_user=current_user,
        db=db,
    )


@router.post("/editor/{candidate_assessment_id}/{round_key}/recompute", status_code=status.HTTP_200_OK)
async def recompute_editor_telemetry(
    candidate_assessment_id: str,
    round_key: str,
    submitted_code: str = "",
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Administrative endpoint to recompute telemetry features and review flags from stored batches."""
    return await TelemetryService.analyze_round_telemetry(
        candidate_assessment_id=candidate_assessment_id,
        round_key=round_key,
        submitted_code=submitted_code,
        db=db,
    )
