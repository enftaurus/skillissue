"""E29-E32: malformed evaluation model output and dispute edge cases (QA report Round 3g)."""
import math
import uuid
from types import SimpleNamespace

import pytest

from backend.app.evaluations.sanitize import coerce_score, dimension_scores, question_index, sanitize_evaluation
from backend.app.providers.base import ProviderResponse
from backend.app.providers.factory import ModelFactory


def test_coerce_score_rejects_nan_and_junk_and_clamps():
    assert coerce_score(float("nan")) is None
    assert coerce_score(float("inf")) is None
    assert coerce_score(True) is None
    assert coerce_score("four") is None
    assert coerce_score(None) is None
    assert coerce_score("4") == 4 and coerce_score("4/5") == 4 and coerce_score(" 3.6 ") == 4
    assert coerce_score(9) == 5 and coerce_score(0) == 1 and coerce_score(-3) == 1


def test_dimension_scores_shapes():
    dims = dimension_scores({"a": 4, "b": {"score": "nan", "explanation": None}, "c": {"score": 2, "evidence_quote": ["x", "y"]}, "": 3})
    assert dims["a"] == {"score": 4, "explanation": "", "evidence_quote": ""}
    assert "score" not in dims["b"] and dims["b"]["explanation"] == ""
    assert dims["c"]["evidence_quote"] == "x, y"
    assert "" not in dims
    assert dimension_scores("garbage") == {}


def test_lists_and_indices():
    p = sanitize_evaluation({"strengths": "one string", "weaknesses": [{"topic": "Caching"}, None, 3],
                             "evidence_excerpts": ["bare quote", {"quote": "q", "critique": None}, 5, {"critique": "no quote"}],
                             "question_feedback": "nope", "weakness_analysis": [1, {"topic": "x"}]})
    assert p["strengths"] == ["one string"] and p["weaknesses"] == ["Caching", "3"]
    assert p["evidence_excerpts"] == [{"quote": "bare quote", "critique": ""}, {"quote": "q", "critique": ""}]
    assert p["question_feedback"] == [] and p["weakness_analysis"] == [{"topic": "x"}]
    assert question_index("Q2", 9) == 2 and question_index(None, 7) == 7 and question_index(True, 1) == 1
    assert question_index(float("nan"), 3) == 3


class _BadEvalProvider:
    model_id = "fake"

    def __init__(self, parsed):
        self.parsed = parsed

    async def generate_json(self, prompt, system_prompt=None, **kw):
        return ProviderResponse(text="{}", parsed_json=self.parsed, input_tokens=1, output_tokens=1, model_id="fake")

    async def generate_text(self, prompt, system_prompt=None, **kw):
        return SimpleNamespace(text='{"decision": "revised", "new_score": NaN, "reason": "x"}')


async def _user_with_answer(client):
    email = f"san_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    h = {"Authorization": "Bearer " + (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]}
    iid = (await client.post("/api/v1/interviews/domain", headers=h, json={"category": "technical", "domain_skills": ["Python"]})).json()["id"]
    answer = "We picked PgBouncer in transaction mode because connection count was the bottleneck at 800 clients."
    await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": answer, "client_turn_id": str(uuid.uuid4())})
    await client.post(f"/api/v1/interviews/{iid}/end", headers=h)
    return h, iid


@pytest.mark.asyncio
async def test_malformed_model_evaluation_no_500_and_nan_not_full_marks(client, monkeypatch):
    h, iid = await _user_with_answer(client)
    parsed = {
        "overall_score": "NaN",
        "dimension_scores": {
            "technical_depth": {"score": float("nan"), "explanation": None},
            "system_design_tradeoffs": 2,
            "communication_clarity": {"score": "five"},
            "problem_solving_rigor": {"score": 9, "evidence_quote": None},
        },
        "strengths": "Knows PgBouncer",
        "weaknesses": [{"topic": "Pool sizing"}],
        "evidence_excerpts": ["PgBouncer in transaction mode", 42],
        "question_feedback": [{"question_index": "Q1", "score": 0, "targeted_resource": {"title": "PgBouncer docs", "url": "https://x"},
                               "critique": None}],
        "uncertainty_notes": None,
    }

    async def _factory(*a, **k):
        return _BadEvalProvider(parsed)
    monkeypatch.setattr(ModelFactory, "get_for_user", _factory)

    r = await client.post(f"/api/v1/evaluations/{iid}/generate", headers=h)
    assert r.status_code in (200, 201), r.text
    ev = r.json()
    dims = ev["rubric_dimension_scores"]
    assert "score" not in dims["technical_depth"]  # NaN dropped, not treated as a 5
    assert dims["system_design_tradeoffs"]["score"] == 2 and dims["problem_solving_rigor"]["score"] == 5
    assert ev["strengths"] == ["Knows PgBouncer"] and ev["weaknesses"] == ["Pool sizing"]
    assert ev["overall_score"] is not None and math.isfinite(ev["overall_score"]) and ev["overall_score"] < 100
    qf = ev["question_feedback"][0]
    assert qf["question_index"] == 1 and qf["score"] == 1 and qf["targeted_resource"] == "PgBouncer docs"
    assert (await client.get(f"/api/v1/evaluations/{iid}", headers=h)).status_code == 200
    assert (await client.get(f"/api/v1/evaluations/{iid}/comparison", headers=h)).status_code in (200, 404)

    # Judge returns NaN as the new score: original stands, no 500.
    d = await client.post(f"/api/v1/evaluations/{iid}/disputes", headers=h,
                          json={"dimension_id": "system_design_tradeoffs", "quote": "PgBouncer in transaction mode because",
                                "argument": "This is a concrete trade-off."})
    assert d.status_code == 201, d.text
    assert d.json()["decision"] == "upheld"


@pytest.mark.asyncio
async def test_dispute_cannot_lift_conduct_cap(client, monkeypatch, db_session):
    from sqlalchemy import select, update
    from backend.app.database.models import Evaluation, Interview
    h, iid = await _user_with_answer(client)
    await db_session.execute(update(Interview).where(Interview.id == iid).values(termination_reason="abusive language"))
    await db_session.commit()
    ev = (await client.post(f"/api/v1/evaluations/{iid}/generate", headers=h)).json()
    assert ev["overall_score"] <= 25
    dim = next(k for k, v in ev["rubric_dimension_scores"].items() if v.get("score", 5) <= 3)

    class _Judge:
        async def generate_text(self, prompt, system_prompt=None, **kw):
            return SimpleNamespace(text='{"decision": "revised", "new_score": 5, "reason": "Fine."}')

    async def _factory(*a, **k):
        return _Judge()
    monkeypatch.setattr(ModelFactory, "get_for_user", _factory)
    r = await client.post(f"/api/v1/evaluations/{iid}/disputes", headers=h,
                          json={"dimension_id": dim, "quote": "PgBouncer in transaction mode because", "argument": "Concrete trade-off."})
    assert r.status_code == 201, r.text
    overall = (await db_session.execute(select(Evaluation.overall_score).where(Evaluation.interview_id == iid))).scalar_one()
    assert overall <= 25
