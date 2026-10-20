import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.errors import AppException
from backend.app.database.models import User, Interview, InterviewMessage, UserSkill, Evaluation, SelfEvaluation
from backend.app.interviews.agent.checkpoint import get_interview_checkpointer
from backend.app.interviews.agent.nodes import prepare_context_node, assess_candidate_turn_node
from backend.app.interviews.agent.state import InterviewAgentState
from backend.app.interviews.service import InterviewService
from backend.app.evaluations.service import EvaluationService

@pytest.mark.asyncio
async def test_production_checkpointer_fails_closed():
    """In production, failure to connect to PostgreSQL checkpointer must fail closed with 503."""
    with patch.object(settings, "ENVIRONMENT", "production"):
        with patch("backend.app.interviews.agent.checkpoint.AsyncPostgresSaver.from_conn_string", side_effect=ConnectionError("Database unavailable")):
            with pytest.raises(AppException) as exc_info:
                async with get_interview_checkpointer() as _:
                    pass
            assert exc_info.value.code == "CHECKPOINT_PERSISTENCE_FAILED"
            assert exc_info.value.status_code == 503

def test_continuous_rolling_summary_updates():
    """Rolling summary must continuously update when conversation exceeds MAX_RECENT_TURNS window."""
    # 8 messages: 4 turns
    messages = [
        {"role": "assistant", "content": f"Question {i}"} if i % 2 == 1 else {"role": "user", "content": f"Answer {i}: I scaled the system using partitioned raft clusters."}
        for i in range(1, 9)
    ]
    state: InterviewAgentState = {
        "recent_messages": messages,
        "running_summary": "Initial summary.",
        "covered_topics": ["Architecture"],
        "current_topic": "Databases",
        "topic_statuses": {"Architecture": "assessed", "Databases": "in_progress"},
    }

    result = prepare_context_node(state)
    assert len(result["recent_messages"]) == 6  # bounded to last 6 messages
    assert "Covered topics: Architecture, Databases" in result["running_summary"]
    assert "raft clusters" in result["running_summary"]

@pytest.mark.asyncio
async def test_topic_lifecycle_progression_no_keywords():
    """Agent must advance through explicit topic lifecycle states without keyword matching."""
    state: InterviewAgentState = {
        "turn_count": 1,
        "max_turns": 8,
        "latest_candidate_answer": "We configured standard database pooling and batch sizes.",
        "difficulty": "intermediate",
        "current_topic": "Database Design",
        "domain_skills": ["Database Design", "Caching Strategies", "Concurrency"],
        "covered_topics": ["Database Design"],
        "topic_statuses": {"Database Design": "in_progress", "Caching Strategies": "not_started", "Concurrency": "not_started"},
        "pending_follow_up": False,
        "candidate_evidence": [],
    }

    # First turn: substantial answer triggers next question or follow-up probe and sets status to needs_follow_up
    decision1 = await assess_candidate_turn_node(state)
    assert decision1["next_action"] in ("ask_follow_up", "next_topic")
    assert decision1["topic_statuses"]["Database Design"] in ("needs_follow_up", "assessed")

    # Following up: when pending_follow_up is True, answering resolves the topic to 'assessed'
    state["pending_follow_up"] = True
    state["topic_statuses"]["Database Design"] = "needs_follow_up"
    state["turn_count"] = 2
    decision2 = await assess_candidate_turn_node(state)
    assert decision2["topic_statuses"]["Database Design"] == "assessed"
    assert decision2["next_action"] == "next_topic"
    assert decision2["current_topic"] == "Caching Strategies"

@pytest.mark.asyncio
async def test_evaluation_skill_update_idempotency(db_session: AsyncSession):
    """Applying the same evaluation multiple times must not compound EMA skill score."""
    from sqlalchemy import select
    user_id = "test-user-idempotency"

    # Ensure user exists
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=f"{user_id}@example.com", hashed_password="hashed_pw_test")
        db_session.add(user)
        await db_session.commit()

    eval_id = "eval-unique-123"
    topic = "distributed_systems"

    # Initial update
    await EvaluationService._update_user_skill(db_session, user_id, topic, 80.0, eval_id)
    await db_session.commit()

    skill = (await db_session.execute(
        select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.topic == topic)
    )).scalar_one_or_none()
    assert skill is not None
    initial_score = skill.score
    assert len(skill.evidence_refs) == 1

    # Second call with same evaluation ID
    await EvaluationService._update_user_skill(db_session, user_id, topic, 80.0, eval_id)
    await db_session.commit()

    skill_after = (await db_session.execute(
        select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.topic == topic)
    )).scalar_one_or_none()
    assert skill_after.score == initial_score
    assert len(skill_after.evidence_refs) == 1

@pytest.mark.asyncio
async def test_turn_idempotency_with_client_turn_id(db_session: AsyncSession):
    """Submitting the same client_turn_id must return the existing assistant message without re-processing."""
    from sqlalchemy import select
    user_id = "test-user-turn-idemp"
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        user = User(id=user_id, email="turn_idemp@example.com", hashed_password="hashed_pw_test")
        db_session.add(user)
        await db_session.commit()

    interview = Interview(
        user_id=user_id,
        mode="domain",
        category="technical",
        title="Technical Interview",
        status="in_progress",
        domain_skills=["Architecture", "Databases"],
        topic_statuses={"Architecture": "in_progress", "Databases": "not_started"},
    )
    db_session.add(interview)
    await db_session.flush()

    msg1 = InterviewMessage(
        interview_id=interview.id,
        role="assistant",
        content="Tell me about how you handled database replication.",
        question_index=1,
    )
    db_session.add(msg1)
    await db_session.commit()

    client_turn_id = "client-turn-uuid-abc-123"

    # Send first message
    assistant_resp1 = await InterviewService.send_message(
        db_session, user_id, interview.id, "We implemented asynchronous multi-region read replicas.", client_turn_id=client_turn_id
    )
    assert assistant_resp1 is not None
    assert assistant_resp1.role == "assistant"

    # Re-send same message with identical client_turn_id (e.g. network retry)
    assistant_resp2 = await InterviewService.send_message(
        db_session, user_id, interview.id, "We implemented asynchronous multi-region read replicas.", client_turn_id=client_turn_id
    )

    # Must return exact same assistant message without creating duplicates
    assert assistant_resp2.id == assistant_resp1.id
    assert assistant_resp2.content == assistant_resp1.content

    # Verify message count in database: exactly 1 initial + 1 user + 1 assistant
    msgs = (await db_session.execute(
        select(InterviewMessage).where(InterviewMessage.interview_id == interview.id)
    )).scalars().all()
    assert len(msgs) == 3
