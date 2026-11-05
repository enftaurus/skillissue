import uuid

import pytest

from backend.app.audio.delivery import delivery_metrics, merge_delivery, summarize_delivery


def test_metrics_from_words_and_text():
    words = [("um", 0, 0.3), ("so", 0.5, 0.7), ("basically", 2.6, 3.0), ("we", 3.1, 3.2), ("uh", 3.3, 3.5),
             ("used", 3.6, 3.8), ("redis", 3.9, 4.3)]
    m = delivery_metrics("um so basically we uh used redis", words=words)
    assert m["fillers"] == {"um": 1, "uh": 1, "basically": 1}
    assert m["long_pauses"] == 1 and m["longest_pause_s"] == 1.9
    assert m["words_per_minute"] == 98
    assert delivery_metrics("Redis made it like ten x faster", 3)["fillers"] == {}  # 'like' as a verb isn't a filler
    assert delivery_metrics("So, like, we used, like, Redis.", 3)["fillers"] == {"like": 2}
    assert delivery_metrics("", 3) is None


def test_merge_sanitizes_client_values():
    m = merge_delivery([{"words": 60, "duration_s": 30, "fillers": {"um": 3}, "hedges": {"i think": 1}},
                        {"words": "x", "duration_s": -5, "fillers": {"um": 1, "a" * 50: 9}, "longest_pause_s": 2.5, "long_pauses": 1}])
    assert m["words"] == 60 and m["duration_s"] == 30 and m["words_per_minute"] == 120
    assert m["fillers"] == {"um": 4} and m["longest_pause_s"] == 2.5
    assert merge_delivery([]) is None


def test_summary_notes():
    s = summarize_delivery([{"words_per_minute": 190, "fillers_per_minute": 6, "fillers": {"um": 9}, "hedge_count": 3},
                            {"words_per_minute": 180, "fillers_per_minute": 5, "fillers": {"like": 2}, "hedge_count": 1}])
    assert s["avg_words_per_minute"] == 185
    assert any("Fast delivery" in n for n in s["notes"]) and any("'um'" in n for n in s["notes"])


@pytest.mark.asyncio
async def test_delivery_is_stored_and_summarized(client):
    email = f"deliv_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    h = {"Authorization": "Bearer " + (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]}
    iid = (await client.post("/api/v1/interviews/domain", headers=h, json={"category": "technical", "domain_skills": ["Python"]})).json()["id"]
    r = await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={
        "content": "Um, I think we used Redis for caching.", "client_turn_id": str(uuid.uuid4()),
        "delivery": [{"words": 8, "duration_s": 4, "fillers": {"um": 1}, "hedges": {"i think": 1}, "longest_pause_s": 1.2, "long_pauses": 0}]})
    assert r.status_code == 200, r.text
    s = (await client.get(f"/api/v1/interviews/{iid}/delivery", headers=h)).json()["summary"]
    assert s["answers_measured"] == 1 and s["avg_words_per_minute"] == 120 and s["hedges"] == 1
