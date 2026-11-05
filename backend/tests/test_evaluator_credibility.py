import uuid
from types import SimpleNamespace

import pytest

from backend.app.evaluations.credibility import confidence, merge_passes
from backend.app.providers.factory import ModelFactory


def test_merge_passes_flags_divergence_and_averages():
    first = {"a": {"score": 5, "explanation": "x"}, "b": {"score": 2, "explanation": "y"}}
    merged, info = merge_passes(first, {"a": {"score": 2}, "b": {"score": 3}})
    assert merged["a"]["score"] == 4 and "disagreed" in merged["a"]["explanation"]
    assert merged["b"]["score"] == 3 and info["divergent_dimensions"] == ["a"] and info["max_gap"] == 3
    assert merge_passes(first, None)[1] == {"passes": 1}


def test_confidence_levels():
    agree = {"divergent_dimensions": []}
    assert confidence(8, 600, {"quotes": 4, "verified": 4}, 6, 6, agree)["level"] == "high"
    assert confidence(2, 40, {"quotes": 0, "verified": 0}, 0, 0, agree)["level"] == "low"
    assert confidence(8, 600, {"quotes": 4, "verified": 1}, 1, 6, agree)["level"] == "low"
    assert confidence(8, 600, {"quotes": 2, "verified": 2}, 2, 2, {"divergent_dimensions": ["a", "b"]})["level"] == "low"


class _Judge:
    def __init__(self, new_score):
        self.new_score = new_score

    async def generate_text(self, prompt, system_prompt=None, **kw):
        return SimpleNamespace(text=f'{{"decision": "revised", "new_score": {self.new_score}, "reason": "Quote shows trade-off reasoning."}}')


@pytest.mark.asyncio
async def test_dispute_flow(client, monkeypatch):
    email = f"disp_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    h = {"Authorization": "Bearer " + (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]}
    iid = (await client.post("/api/v1/interviews/domain", headers=h, json={"category": "technical", "domain_skills": ["Python"]})).json()["id"]
    answer = "We picked PgBouncer in transaction mode because connection count was the bottleneck at 800 clients."
    await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": answer, "client_turn_id": str(uuid.uuid4())})
    await client.post(f"/api/v1/interviews/{iid}/end", headers=h)
    ev = (await client.post(f"/api/v1/evaluations/{iid}/generate", headers=h)).json()
    assert ev["credibility"]["confidence"]["level"] in ("low", "medium", "high")
    assert ev["credibility"]["consistency"]["passes"] == 2
    dim = next(iter(ev["rubric_dimension_scores"]))
    old = ev["rubric_dimension_scores"][dim]["score"]

    r = await client.post(f"/api/v1/evaluations/{iid}/disputes", headers=h,
                          json={"dimension_id": dim, "quote": "I designed Google's entire storage system", "argument": "I am very good at this."})
    assert r.status_code == 400 and r.json()["error"]["code"] == "QUOTE_NOT_IN_TRANSCRIPT"

    async def _judge(*a, **k):
        return _Judge(5)
    monkeypatch.setattr(ModelFactory, "get_for_user", _judge)
    r = await client.post(f"/api/v1/evaluations/{iid}/disputes", headers=h,
                          json={"dimension_id": dim, "quote": "PgBouncer in transaction mode because connection count was the bottleneck",
                                "argument": "This shows a measured trade-off, not a textbook answer."})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["decision"] == "revised" and d["new_score"] == min(5, old + 2) and d["old_score"] == old  # capped at +2
    ev2 = (await client.get(f"/api/v1/evaluations/{iid}", headers=h)).json()
    assert ev2["rubric_dimension_scores"][dim]["score"] == d["new_score"]
    again = await client.post(f"/api/v1/evaluations/{iid}/disputes", headers=h,
                              json={"dimension_id": dim, "quote": "PgBouncer in transaction mode because connection count", "argument": "Again please."})
    assert again.json()["error"]["code"] == "ALREADY_DISPUTED"
    assert len((await client.get(f"/api/v1/evaluations/{iid}/disputes", headers=h)).json()) == 1
