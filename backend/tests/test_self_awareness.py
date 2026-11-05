import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.analytics.self_awareness import self_awareness_report
from backend.app.database.models import Evaluation, Interview, SelfEvaluation


@pytest.mark.asyncio
async def test_gap_trend_and_headline(db_session, create_test_user):
    user = await create_test_user(f"aware_{uuid.uuid4().hex[:6]}@example.com")
    other = await create_test_user(f"aware_o_{uuid.uuid4().hex[:6]}@example.com")
    base = datetime.now(timezone.utc) - timedelta(days=3)
    for owner, i, self_s, ai_s in [(user, 0, 5, 1), (user, 1, 4, 3), (other, 0, 1, 5)]:
        iv = Interview(user_id=owner.id, mode="domain", category="technical", title=f"t{i}", target_role="SWE",
                       difficulty="intermediate", status="completed", domain_skills=["Python"])
        db_session.add(iv)
        await db_session.flush()
        db_session.add(SelfEvaluation(interview_id=iv.id, user_id=owner.id, dimension_scores={"technical_depth": self_s}))
        db_session.add(Evaluation(interview_id=iv.id, user_id=owner.id, overall_score=40.0, created_at=base + timedelta(days=i),
                                  rubric_dimension_scores={"technical_depth": {"score": ai_s}}))
    await db_session.commit()

    r = await self_awareness_report(db_session, user.id)
    d = r["dimensions"][0]
    assert d["dimension_id"] == "technical_depth" and d["samples"] == 2  # other user's data excluded
    assert d["first_gap"] == 4 and d["latest_gap"] == 1 and d["trend"] == 3
    assert d["bias"] == "overrate"
    assert "overrate technical depth" in r["headline"] and "down from 4.0" in r["headline"]
    assert r["index"] == 2.5


@pytest.mark.asyncio
async def test_empty_report(db_session, create_test_user):
    user = await create_test_user(f"aware_e_{uuid.uuid4().hex[:6]}@example.com")
    r = await self_awareness_report(db_session, user.id)
    assert r["index"] is None and r["dimensions"] == [] and r["headline"] is None
