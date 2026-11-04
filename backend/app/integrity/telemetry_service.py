"""Telemetry service for ingesting Monaco editor events, enforcing sequence integrity,
replaying document states, running feature analysis, and generating recruiter replay timelines.

Rule 3 (Integrity Policy): Everything here produces review flags only and must
never alter scores, pass/fail results, or rankings.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.app.core.errors import NotFoundError, AuthorizationError, ValidationError
from backend.app.database.models import (
    CandidateAssessment,
    EditorEventBatch,
    AssessmentPipeline,
    ExplanationCheck,
    User,
    utc_now,
)
from backend.app.integrity.document_reconstructor import (
    reconstruct_document_from_deltas,
    verify_reconstructed_code,
)
from backend.app.integrity.features import extract_all_telemetry_features
from backend.app.integrity.flags import evaluate_telemetry_flags
from backend.app.integrity.triviality import count_effective_lines
from backend.app.integrity.config import PRODUCT_HONESTY_NOTICE
from backend.app.integrity.schemas import (
    EditorTelemetryBatchRequest,
    EditorTelemetryReplayResponse,
)

logger = logging.getLogger("skillissue.integrity")

MAX_EVENTS_PER_BATCH = 500


class TelemetryService:

    @staticmethod
    async def ingest_batch(
        req: EditorTelemetryBatchRequest,
        candidate_assessment: CandidateAssessment,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Ingest editor telemetry batch with sequence monotonicity and batch cap checks."""
        # 1. Cap batch size
        if len(req.events) > MAX_EVENTS_PER_BATCH:
            raise ValidationError(f"Batch size exceeds maximum limit of {MAX_EVENTS_PER_BATCH} events.")

        # 2. Check sequence monotonicity: seq must be strictly greater than max existing seq
        query = (
            select(func.max(EditorEventBatch.seq))
            .where(
                EditorEventBatch.candidate_assessment_id == candidate_assessment.id,
                EditorEventBatch.round_key == req.round_key,
            )
        )
        res = await db.execute(query)
        max_seq = res.scalar()

        if max_seq is not None:
            if req.seq <= max_seq:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"TAMPERED_SEQUENCE: seq {req.seq} is not monotonic (last seen {max_seq}). Replays rejected.",
                )

        # 3. Store batch
        batch = EditorEventBatch(
            candidate_assessment_id=candidate_assessment.id,
            round_key=req.round_key,
            seq=req.seq,
            received_at=utc_now(),
            payload={
                "client_start_ts": req.client_start_ts,
                "events": req.events,
            },
        )
        db.add(batch)
        await db.commit()

        return {"status": "ok", "seq": req.seq, "received_events": len(req.events)}

    @staticmethod
    async def analyze_round_telemetry(
        candidate_assessment_id: str,
        round_key: str,
        submitted_code: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Perform end-of-round telemetry feature extraction and flag generation. Idempotent."""
        # 1. Fetch CandidateAssessment
        ca_q = select(CandidateAssessment).where(CandidateAssessment.id == candidate_assessment_id)
        ca_res = await db.execute(ca_q)
        ca = ca_res.scalar_one_or_none()
        if not ca:
            raise NotFoundError("Candidate assessment not found")

        # 2. Fetch all batches in order
        batch_q = (
            select(EditorEventBatch)
            .where(
                EditorEventBatch.candidate_assessment_id == candidate_assessment_id,
                EditorEventBatch.round_key == round_key,
            )
            .order_by(EditorEventBatch.seq.asc())
        )
        b_res = await db.execute(batch_q)
        batches = b_res.scalars().all()
        if not batches:
            return {
                "status": "not_assessed",
                "reason": "No editor telemetry recorded for this round.",
                "flags": [],
                "triggered_families": [],
                "overall_confidence": None,
                "product_honesty": PRODUCT_HONESTY_NOTICE,
            }

        all_events: List[Dict[str, Any]] = []
        client_start_ts = 0.0
        missing_batches_count = 0

        # Check for sequence continuity
        expected_seq = 0
        for b in batches:
            if b.seq != expected_seq:
                missing_batches_count += (b.seq - expected_seq)
            expected_seq = b.seq + 1

            payload = b.payload or {}
            if client_start_ts == 0.0 and payload.get("client_start_ts"):
                client_start_ts = payload["client_start_ts"]
            all_events.extend(payload.get("events") or [])

        # 3. Reconstruct document from deltas
        reconstructed_code, had_errors, _ = reconstruct_document_from_deltas("", all_events)
        hash_match, _, _ = verify_reconstructed_code(reconstructed_code, submitted_code)

        # 4. Extract telemetry features
        features = extract_all_telemetry_features(
            events=all_events,
            client_start_ts=client_start_ts,
            final_length=len(submitted_code),
        )

        # 5. Check if ExplanationCheck has flagged this candidate
        exp_q = (
            select(ExplanationCheck)
            .where(
                ExplanationCheck.candidate_assessment_id == candidate_assessment_id,
                ExplanationCheck.round_key == round_key,
            )
        )
        exp_res = await db.execute(exp_q)
        exp_check = exp_res.scalar_one_or_none()

        explanation_mismatch = False
        if exp_check and exp_check.evaluation:
            cons = exp_check.evaluation.get("explanation_consistency", 1.0)
            conf = exp_check.confidence
            if conf in {"medium", "high"} and cons < 0.35:
                explanation_mismatch = True

        # 6. Evaluate review flags
        effective_lines = count_effective_lines(submitted_code)
        flag_results = evaluate_telemetry_flags(
            features=features,
            effective_lines=effective_lines,
            total_events=len(all_events),
            code_hash_match=hash_match,
            missing_batches_count=missing_batches_count,
            explanation_mismatch=explanation_mismatch,
        )

        # 7. Update CandidateAssessment integrity_signals (DO NOT touch score or ranking)
        current_signals = dict(ca.integrity_signals or {})
        existing_flags = list(current_signals.get("flags") or [])

        # Merge new flags avoiding duplicates
        existing_codes = {f.get("code") for f in existing_flags}
        for new_f in flag_results["flags"]:
            if new_f.get("code") not in existing_codes:
                existing_flags.append(new_f)

        current_signals["status"] = flag_results["status"]
        current_signals["flags"] = existing_flags
        current_signals["features"] = {
            "typed_ratio": features["typed_ratio"],
            "large_insert_count": features["large_insert_count"],
            "growth_without_activity_count": features["growth_without_activity_count"],
            "revision_ratio": features["revision_ratio"],
            "read_then_type_count": features["read_then_type_count"],
            "blur_count": features["focus"]["blur_count"],
            "total_blurred_seconds": features["focus"]["total_blurred_seconds"],
            "active_time_seconds": features["focus"]["active_time_seconds"],
            "wall_time_seconds": features["focus"]["wall_time_seconds"],
        }
        current_signals["window_blurs"] = features["focus"]["blur_count"]
        current_signals["product_honesty"] = PRODUCT_HONESTY_NOTICE

        ca.integrity_signals = current_signals
        await db.commit()

        return flag_results

    @staticmethod
    async def get_replay_data(
        candidate_assessment_id: str,
        round_key: str,
        current_user: User,
        db: AsyncSession,
    ) -> EditorTelemetryReplayResponse:
        """Fetch telemetry replay timeline and features. Recruiter & Admin only with tenant isolation."""
        # Recruiter / Admin verification
        if current_user.role not in {"recruiter", "admin"}:
            raise AuthorizationError("Only recruiters and administrators may access candidate telemetry replays")

        ca_q = select(CandidateAssessment).where(CandidateAssessment.id == candidate_assessment_id)
        ca_res = await db.execute(ca_q)
        ca = ca_res.scalar_one_or_none()
        if not ca:
            raise NotFoundError("Candidate assessment not found")

        # Tenant isolation
        if current_user.role == "recruiter":
            pipe_q = select(AssessmentPipeline).where(AssessmentPipeline.id == ca.pipeline_id)
            pipe_res = await db.execute(pipe_q)
            pipeline = pipe_res.scalar_one_or_none()
            if not pipeline or pipeline.tenant_id != current_user.tenant_id:
                raise AuthorizationError("Access denied: candidate assessment belongs to another tenant")

        # Fetch batches
        batch_q = (
            select(EditorEventBatch)
            .where(
                EditorEventBatch.candidate_assessment_id == candidate_assessment_id,
                EditorEventBatch.round_key == round_key,
            )
            .order_by(EditorEventBatch.seq.asc())
        )
        b_res = await db.execute(batch_q)
        batches = b_res.scalars().all()

        all_events: List[Dict[str, Any]] = []
        client_start_ts = 0.0
        for b in batches:
            payload = b.payload or {}
            if client_start_ts == 0.0 and payload.get("client_start_ts"):
                client_start_ts = payload["client_start_ts"]
            all_events.extend(payload.get("events") or [])

        round_data = (ca.round_results or {}).get(str(round_key)) or {}
        sub_code = (
            round_data.get("submission", {}).get("code")
            or ca.oa_submitted_code
            or ""
        )

        reconstructed_code, _, _ = reconstruct_document_from_deltas("", all_events)
        hash_match, _, _ = verify_reconstructed_code(reconstructed_code, sub_code)

        features = extract_all_telemetry_features(all_events, client_start_ts, len(sub_code))

        # Build timeline markers for paste, large insert, blur, idle gaps
        timeline_markers = []
        timeline = []
        doc = ""
        is_ms = client_start_ts > 10_000_000_000 or (all_events and all_events[0].get("timestamp", 0) > 10_000_000_000)
        div = 1000.0 if is_ms else 1.0
        base_ts = client_start_ts if client_start_ts > 0 else (all_events[0].get("timestamp", 0) if all_events else 0)

        for e in all_events:
            ev_type = e.get("type")
            ts = e.get("timestamp", 0)
            offset_s = max(0.0, round((ts - base_ts) / div, 1))

            if ev_type in {"content_change", "paste", "key_down"} and "inserted_text" in e:
                ins = e.get("inserted_text") or ""
                off = e.get("range_offset")
                l = e.get("range_length", 0)
                if off is not None and 0 <= off <= len(doc):
                    doc = doc[:off] + ins + doc[min(len(doc), off + l):]
                else:
                    doc += ins

            marker_type = None
            marker_label = None
            if ev_type == "paste":
                marker_type = "paste"
                marker_label = f"Paste (+{e.get('inserted_length', 0)} chars)"
                timeline_markers.append({"timestamp": ts, "type": "paste", "label": marker_label})
            elif ev_type == "blur":
                marker_type = "blur"
                marker_label = "Window focus loss"
                timeline_markers.append({"timestamp": ts, "type": "blur", "label": marker_label})
            elif e.get("inserted_length", 0) >= 80 and e.get("source") != "typing":
                marker_type = "large_insert"
                marker_label = f"Large insert (+{e.get('inserted_length', 0)} chars)"
                timeline_markers.append({"timestamp": ts, "type": "large_insert", "label": marker_label})

            timeline.append({
                "timestamp": ts,
                "offset_seconds": offset_s,
                "text": doc,
                "char_count": len(doc),
                "event_type": ev_type,
                "source": e.get("source", "typing"),
                "marker_type": marker_type,
                "marker_label": marker_label,
            })

        if not timeline:
            timeline = [{
                "timestamp": 0,
                "offset_seconds": 0.0,
                "text": sub_code,
                "char_count": len(sub_code),
                "event_type": "initial",
                "source": "typing",
                "marker_type": None,
                "marker_label": None,
            }]

        # Activity density series per 10-30s
        density_series = features.get("activity_density_series") or []
        flags = (ca.integrity_signals or {}).get("flags") or []
        signals_features = (ca.integrity_signals or {}).get("features") or features

        return EditorTelemetryReplayResponse(
            candidate_assessment_id=candidate_assessment_id,
            round_key=round_key,
            total_batches=len(batches),
            total_events=len(all_events),
            reconstructed_code=reconstructed_code,
            code_hash_match=hash_match,
            features=signals_features,
            flags=flags,
            activity_density_series=density_series,
            timeline_markers=timeline_markers,
            timeline=timeline,
            product_honesty=PRODUCT_HONESTY_NOTICE,
        )
