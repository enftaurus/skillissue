"""Tests for Editor Telemetry, server-side activity analysis, and recruiter replay.

Verifies:
1. Human-like stream with revisions and pauses produces zero flags.
2. A single 600-character paste produces LARGE_UNTYPED_INSERT at low confidence.
3. Paste + no activity + failed explanation check produces medium confidence (two independent families).
4. Hand-typed transcription pattern produces at most low READ_THEN_TYPE_PATTERN.
5. Monaco suggestion inserting 30 characters does not trigger large-insert flag.
6. Short solution or short session produces insufficient_data and zero flags.
7. Out-of-order/tampered sequence is rejected with 400, missing batches yield TELEMETRY_INCOMPLETE info flag.
8. Scores, pass/fail, and rankings are identical with and without flags.
9. Tenant isolation on telemetry replay endpoints.
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.database.models import (
    User, Tenant, AssessmentPipeline, CandidateAssessment, EditorEventBatch
)
from backend.app.integrity.telemetry_service import TelemetryService
from backend.app.integrity.schemas import EditorTelemetryBatchRequest
from backend.app.integrity.features import extract_all_telemetry_features
from backend.app.integrity.flags import evaluate_telemetry_flags
from backend.app.integrity.config import (
    MIN_EVIDENCE_EFFECTIVE_LINES,
    MIN_EVIDENCE_ACTIVE_TIME_SECONDS,
    MIN_EVIDENCE_EDIT_EVENTS,
)


@pytest.fixture
async def setup_telemetry_env(db_session: AsyncSession):
    """Setup isolated tenant, recruiter, pipeline, and candidate."""
    t_id = f"ten_tel_{uuid.uuid4().hex[:8]}"
    tenant = Tenant(id=t_id, name="Telemetry Org", slug=t_id, is_test=True)
    db_session.add(tenant)

    recruiter = User(
        id=f"rec_t_{uuid.uuid4().hex[:8]}",
        email=f"rec_t_{uuid.uuid4().hex[:8]}@tel.com",
        hashed_password="Hash",
        role="recruiter",
        tenant_id=tenant.id,
        is_test=True,
    )
    db_session.add(recruiter)
    await db_session.flush()

    pipeline = AssessmentPipeline(
        id=f"pipe_t_{uuid.uuid4().hex[:8]}",
        created_by_user_id=recruiter.id,
        tenant_id=tenant.id,
        title="Infrastructure Drive",
        target_role="Systems Engineer",
        job_description="Concurrent Go and Python",
        rounds=[{"round_type": "oa_dsa", "name": "OA DSA", "time_limit_minutes": 45, "is_enabled": True}],
        invite_token=f"inv_t_{uuid.uuid4().hex[:12]}",
    )
    db_session.add(pipeline)

    cand_token = f"cand_tok_{uuid.uuid4().hex[:16]}"
    # 15-line non-trivial code
    code_lines = [
        "def solve(nums):",
        "    if not nums:",
        "        return []",
        "    freq = {}",
        "    for x in nums:",
        "        freq[x] = freq.get(x, 0) + 1",
        "    buckets = [[] for _ in range(len(nums) + 1)]",
        "    for val, count in freq.items():",
        "        buckets[count].append(val)",
        "    result = []",
        "    for i in range(len(buckets) - 1, 0, -1):",
        "        for v in buckets[i]:",
        "            result.append(v)",
        "            if len(result) == 2:",
        "                return result",
        "    return result",
    ]
    full_code = "\n".join(code_lines) + "\n"

    candidate = CandidateAssessment(
        id=f"cand_t_{uuid.uuid4().hex[:8]}",
        pipeline_id=pipeline.id,
        candidate_name="Grace Hopper",
        candidate_email=f"grace_{uuid.uuid4().hex[:8]}@navy.mil",
        access_token=cand_token,
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        status="in_progress",
        oa_problem_title="Top K Frequent Elements",
        oa_submitted_code=full_code,
        current_round_index=0,
        round_results={
            "0": {
                "round_type": "oa_dsa",
                "score": 92.0,
                "status": "scored",
                "submission": {"code": full_code},
            }
        },
        composite_score=92.0,
        integrity_signals={"status": "not_assessed", "flags": []},
    )
    db_session.add(candidate)
    await db_session.commit()

    return {
        "tenant": tenant,
        "recruiter": recruiter,
        "pipeline": pipeline,
        "candidate": candidate,
        "full_code": full_code,
    }


def generate_human_like_events(code: str) -> list:
    """Generate human-like events: typing a real multiline solution with variable timing over > 4 minutes."""
    events = []
    base_ts = 1700000000000.0  # ms
    current_offset = 0

    for i, ch in enumerate(code):
        gap = 800 + ((i * 37) % 200)
        base_ts += gap
        events.append({
            "type": "key_down",
            "timestamp": base_ts,
            "key_category": "enter" if ch == "\n" else "printable",
            "source": "typing",
            "inserted_length": 1,
            "line_count_delta": 1 if ch == "\n" else 0,
            "range_offset": current_offset,
            "range_length": 0,
            "inserted_text": ch,
        })
        current_offset += 1

        # Occasional backspace revisions
        if i % 40 == 0 and current_offset > 2:
            base_ts += 250
            # Remove a char
            events.append({
                "type": "key_down",
                "timestamp": base_ts,
                "key_category": "backspace_delete",
                "source": "typing",
                "inserted_length": 0,
                "removed_length": 1,
                "range_offset": current_offset - 1,
                "range_length": 1,
                "inserted_text": "",
            })
            current_offset -= 1
            # Re-type the char
            base_ts += 300
            events.append({
                "type": "key_down",
                "timestamp": base_ts,
                "key_category": "enter" if ch == "\n" else "printable",
                "source": "typing",
                "inserted_length": 1,
                "line_count_delta": 1 if ch == "\n" else 0,
                "range_offset": current_offset,
                "range_length": 0,
                "inserted_text": ch,
            })
            current_offset += 1

    return events


@pytest.mark.asyncio
async def test_human_like_stream_produces_zero_flags(setup_telemetry_env, db_session: AsyncSession):
    """Verify that a natural human-like editing stream with revisions and pauses produces zero flags."""
    env = setup_telemetry_env
    cand = env["candidate"]

    events = generate_human_like_events(env["full_code"])
    batch_req = EditorTelemetryBatchRequest(
        round_key="0",
        seq=0,
        client_start_ts=events[0]["timestamp"],
        events=events,
    )

    await TelemetryService.ingest_batch(batch_req, cand, db_session)

    from backend.app.integrity.document_reconstructor import reconstruct_document_from_deltas
    reconstructed_text, _, _ = reconstruct_document_from_deltas("", events)

    # Run analysis
    res = await TelemetryService.analyze_round_telemetry(
        candidate_assessment_id=cand.id,
        round_key="0",
        submitted_code=reconstructed_text,
        db=db_session,
    )

    assert res["status"] == "evaluated"
    assert len(res["flags"]) == 0
    assert len(res["triggered_families"]) == 0
    assert res["overall_confidence"] is None

    # Verify candidate assessment scores are completely unaltered
    await db_session.refresh(cand)
    assert cand.round_results["0"]["score"] == 92.0
    assert cand.composite_score == 92.0


@pytest.mark.asyncio
async def test_single_large_paste_produces_large_untyped_insert_at_low_confidence(
    setup_telemetry_env, db_session: AsyncSession
):
    """Verify that a single 600-character paste produces LARGE_UNTYPED_INSERT flag at low confidence (one family)."""
    env = setup_telemetry_env
    cand = env["candidate"]

    base_ts = 1700000000000.0
    events = []

    # 210 typing events spread across 200 seconds to pass minimum evidence gates
    for i in range(210):
        base_ts += 1000
        events.append({
            "type": "key_down",
            "timestamp": base_ts,
            "key_category": "printable",
            "source": "typing",
            "inserted_length": 1,
            "range_offset": i,
            "range_length": 0,
            "inserted_text": "a",
        })

    # One 600-character paste event
    base_ts += 2000
    events.append({
        "type": "paste",
        "timestamp": base_ts,
        "source": "paste",
        "inserted_length": 600,
        "line_count_delta": 12,
        "range_offset": 210,
        "range_length": 0,
        "inserted_text": "pasted_text" * 50,
    })

    batch_req = EditorTelemetryBatchRequest(
        round_key="0",
        seq=0,
        client_start_ts=events[0]["timestamp"],
        events=events,
    )
    await TelemetryService.ingest_batch(batch_req, cand, db_session)

    res = await TelemetryService.analyze_round_telemetry(
        candidate_assessment_id=cand.id,
        round_key="0",
        submitted_code=env["full_code"],
        db=db_session,
    )

    assert res["status"] == "evaluated"
    review_flags = [f for f in res["flags"] if f.get("code") == "LARGE_UNTYPED_INSERT"]
    assert len(review_flags) == 1
    # Exactly one family triggered (insertion_source) -> low confidence
    assert review_flags[0]["confidence"] == "low"
    assert review_flags[0]["severity"] == "review"
    assert "evidence" in review_flags[0]

    # Scores untouched
    await db_session.refresh(cand)
    assert cand.round_results["0"]["score"] == 92.0


@pytest.mark.asyncio
async def test_paste_plus_explanation_mismatch_gives_medium_confidence(
    setup_telemetry_env, db_session: AsyncSession
):
    """Verify that multiple independent families (paste in telemetry + failed explanation check) escalate confidence to medium."""
    env = setup_telemetry_env
    cand = env["candidate"]

    # 1. Attach a failed ExplanationCheck with low consistency to candidate
    from backend.app.database.models import ExplanationCheck
    exp_check = ExplanationCheck(
        candidate_assessment_id=cand.id,
        round_key="0",
        submission_ref="oa_sub",
        mode="assessment",
        status="evaluated",
        confidence="medium",
        discriminative_power="normal",
        questions=[{"text": "Why Kahn's algorithm?", "code_reference": "in_degree"}],
        answers=[{"text": "I don't know, completely copied from internet."}],
        evaluation={
            "explanation_consistency": 0.2,
            "question_evaluations": [{"accuracy": 1, "consistency": 1, "depth": 1}],
        },
    )
    db_session.add(exp_check)
    await db_session.commit()

    # 2. Ingest telemetry with 600-char paste and 210 events over 200s
    base_ts = 1700000000000.0
    events = []
    for i in range(210):
        base_ts += 1000
        events.append({
            "type": "key_down",
            "timestamp": base_ts,
            "key_category": "printable",
            "source": "typing",
            "inserted_length": 1,
            "range_offset": i,
            "range_length": 0,
            "inserted_text": "x",
        })

    events.append({
        "type": "paste",
        "timestamp": base_ts + 2000,
        "source": "paste",
        "inserted_length": 600,
        "line_count_delta": 15,
        "range_offset": 210,
        "range_length": 0,
        "inserted_text": "pasted_solution" * 40,
    })

    batch_req = EditorTelemetryBatchRequest(
        round_key="0",
        seq=0,
        client_start_ts=events[0]["timestamp"],
        events=events,
    )
    await TelemetryService.ingest_batch(batch_req, cand, db_session)

    res = await TelemetryService.analyze_round_telemetry(
        candidate_assessment_id=cand.id,
        round_key="0",
        submitted_code=env["full_code"],
        db=db_session,
    )

    # Two independent families triggered: insertion_source and explanation
    assert "insertion_source" in res["triggered_families"]
    assert "explanation" in res["triggered_families"]
    assert res["overall_confidence"] == "medium"

    review_flags = [f for f in res["flags"] if f.get("code") == "LARGE_UNTYPED_INSERT"]
    assert review_flags[0]["confidence"] == "medium"


@pytest.mark.asyncio
async def test_hand_typed_transcription_produces_at_most_low_read_then_type(
    setup_telemetry_env, db_session: AsyncSession
):
    """Verify that an idle pause followed by high-speed typing triggers READ_THEN_TYPE_PATTERN at low confidence."""
    env = setup_telemetry_env
    cand = env["candidate"]

    base_ts = 1700000000000.0
    events = []

    # 1. 100 initial events
    for i in range(100):
        base_ts += 1000
        events.append({
            "type": "key_down",
            "timestamp": base_ts,
            "key_category": "printable",
            "source": "typing",
            "inserted_length": 1,
            "range_offset": i,
            "range_length": 0,
            "inserted_text": "x",
        })

    # 2. Idle pause of 75 seconds (>= 60s)
    base_ts += 75000

    # 3. Fast typing burst: 160 characters within 15 seconds (>= 150 chars in <= 20s)
    for j in range(160):
        base_ts += 90  # 90ms per key
        events.append({
            "type": "key_down",
            "timestamp": base_ts,
            "key_category": "printable",
            "source": "typing",
            "inserted_length": 1,
            "range_offset": 100 + j,
            "range_length": 0,
            "inserted_text": "c",
        })

    batch_req = EditorTelemetryBatchRequest(
        round_key="0",
        seq=0,
        client_start_ts=events[0]["timestamp"],
        events=events,
    )
    await TelemetryService.ingest_batch(batch_req, cand, db_session)

    res = await TelemetryService.analyze_round_telemetry(
        candidate_assessment_id=cand.id,
        round_key="0",
        submitted_code=env["full_code"],
        db=db_session,
    )

    rtt_flags = [f for f in res["flags"] if f.get("code") == "READ_THEN_TYPE_PATTERN"]
    assert len(rtt_flags) == 1
    # READ_THEN_TYPE_PATTERN alone must always be low confidence
    assert rtt_flags[0]["confidence"] == "low"
    assert rtt_flags[0]["severity"] == "review"


@pytest.mark.asyncio
async def test_monaco_suggestion_does_not_trigger_large_insert(
    setup_telemetry_env, db_session: AsyncSession
):
    """Verify that inline autocomplete or Monaco suggestion inserting 30 chars with source='suggest' is ignored by large_insert."""
    env = setup_telemetry_env
    cand = env["candidate"]

    base_ts = 1700000000000.0
    events = []
    for i in range(210):
        base_ts += 1000
        events.append({
            "type": "key_down",
            "timestamp": base_ts,
            "key_category": "printable",
            "source": "typing",
            "inserted_length": 1,
            "range_offset": i,
            "range_length": 0,
            "inserted_text": "s",
        })

    # Monaco suggestion insert of 30 characters
    events.append({
        "type": "content_change",
        "timestamp": base_ts + 500,
        "source": "suggest",
        "inserted_length": 30,
        "range_offset": 210,
        "range_length": 0,
        "inserted_text": "autocomplete_variable_name_123",
    })

    batch_req = EditorTelemetryBatchRequest(
        round_key="0",
        seq=0,
        client_start_ts=events[0]["timestamp"],
        events=events,
    )
    await TelemetryService.ingest_batch(batch_req, cand, db_session)

    res = await TelemetryService.analyze_round_telemetry(
        candidate_assessment_id=cand.id,
        round_key="0",
        submitted_code=env["full_code"],
        db=db_session,
    )

    assert not any(f.get("code") == "LARGE_UNTYPED_INSERT" for f in res["flags"])


@pytest.mark.asyncio
async def test_short_solution_or_brief_session_yields_insufficient_data(
    setup_telemetry_env, db_session: AsyncSession
):
    """Verify that sessions under 3 minutes or < 10 effective lines return insufficient_data and raise ZERO flags."""
    env = setup_telemetry_env
    cand = env["candidate"]

    # Short solution: only 4 lines
    short_code = "def short():\n    return 42\n"
    cand.oa_submitted_code = short_code

    # Brief session: only 15 events over 20 seconds
    base_ts = 1700000000000.0
    events = [
        {"type": "key_down", "timestamp": base_ts + (i * 1000), "source": "typing", "inserted_length": 1}
        for i in range(15)
    ]

    batch_req = EditorTelemetryBatchRequest(
        round_key="0",
        seq=0,
        client_start_ts=base_ts,
        events=events,
    )
    await TelemetryService.ingest_batch(batch_req, cand, db_session)

    res = await TelemetryService.analyze_round_telemetry(
        candidate_assessment_id=cand.id,
        round_key="0",
        submitted_code=short_code,
        db=db_session,
    )

    assert res["status"] == "insufficient_data"
    assert len(res["flags"]) == 0
    assert "under the minimum threshold" in res["reason"]


@pytest.mark.asyncio
async def test_tampered_sequence_rejected_and_missing_batch_produces_info_only(
    setup_telemetry_env, db_session: AsyncSession
):
    """Verify that non-monotonic batch sequence is rejected with 400, while gaps produce TELEMETRY_INCOMPLETE info note."""
    env = setup_telemetry_env
    cand = env["candidate"]

    base_ts = 1700000000000.0
    batch_0 = EditorTelemetryBatchRequest(
        round_key="0",
        seq=0,
        client_start_ts=base_ts,
        events=[{"type": "key_down", "timestamp": base_ts, "source": "typing", "inserted_length": 1}],
    )
    await TelemetryService.ingest_batch(batch_0, cand, db_session)

    # Ingesting seq=0 again or lower seq must be rejected
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await TelemetryService.ingest_batch(batch_0, cand, db_session)
    assert exc_info.value.status_code == 400
    assert "TAMPERED_SEQUENCE" in str(exc_info.value.detail)

    # Ingesting batch with gap (e.g. seq=3 after seq=0)
    batch_gap = EditorTelemetryBatchRequest(
        round_key="0",
        seq=3,
        client_start_ts=base_ts,
        events=[{"type": "key_down", "timestamp": base_ts + 200000, "source": "typing", "inserted_length": 1}] * 210,
    )
    await TelemetryService.ingest_batch(batch_gap, cand, db_session)

    res = await TelemetryService.analyze_round_telemetry(
        candidate_assessment_id=cand.id,
        round_key="0",
        submitted_code=env["full_code"],
        db=db_session,
    )

    # Must include info-level TELEMETRY_INCOMPLETE
    incomplete_flags = [f for f in res["flags"] if f.get("code") == "TELEMETRY_INCOMPLETE"]
    assert len(incomplete_flags) == 1
    assert incomplete_flags[0]["severity"] == "info"


@pytest.mark.asyncio
async def test_tenant_isolation_on_replay_data(setup_telemetry_env, db_session: AsyncSession):
    """Verify that recruiter from Tenant B cannot access candidate telemetry replay from Tenant A."""
    env = setup_telemetry_env
    cand = env["candidate"]

    # Ingest a sample batch
    base_ts = 1700000000000.0
    batch = EditorTelemetryBatchRequest(
        round_key="0",
        seq=0,
        client_start_ts=base_ts,
        events=[{"type": "key_down", "timestamp": base_ts, "source": "typing", "inserted_length": 1}],
    )
    await TelemetryService.ingest_batch(batch, cand, db_session)

    # Create recruiter B in Tenant B
    tenant_b = Tenant(id=f"ten_b_{uuid.uuid4().hex[:8]}", name="Other Org", slug=f"slug_{uuid.uuid4().hex[:8]}")
    db_session.add(tenant_b)
    recruiter_b = User(
        id=f"rec_b_{uuid.uuid4().hex[:8]}",
        email=f"rec_b_{uuid.uuid4().hex[:8]}@other.com",
        hashed_password="Hash",
        role="recruiter",
        tenant_id=tenant_b.id,
    )
    db_session.add(recruiter_b)
    await db_session.commit()

    from backend.app.core.errors import AuthorizationError
    with pytest.raises(AuthorizationError):
        await TelemetryService.get_replay_data(
            candidate_assessment_id=cand.id,
            round_key="0",
            current_user=recruiter_b,
            db=db_session,
        )

    # Recruiter A from Tenant A succeeds
    replay = await TelemetryService.get_replay_data(
        candidate_assessment_id=cand.id,
        round_key="0",
        current_user=env["recruiter"],
        db=db_session,
    )
    assert replay.candidate_assessment_id == cand.id
    assert replay.round_key == "0"
    assert replay.total_batches == 1
    assert "product_honesty" in replay.model_dump()
