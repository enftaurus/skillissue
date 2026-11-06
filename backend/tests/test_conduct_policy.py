"""Conduct policy: warn once, then end the interview, with the outcome reflected in the evaluation."""
import uuid

import pytest

from backend.app.interviews import conduct


async def _login(client):
    email = f"conduct_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    tok = (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


async def _interview(client, h, category="technical"):
    r = await client.post("/api/v1/interviews/domain", headers=h, json={
        "category": category, "domain_skills": ["Python", "PostgreSQL"], "target_role": "Backend Engineer", "difficulty": "intermediate"})
    assert r.status_code == 201
    return r.json()["id"]


def test_quick_verdicts_and_false_positive_safety():
    for bad in ("I copied it from leetcode", "honestly chatgpt wrote this code", "what the fuck is this", "shut up",
                "My friend wrote it for me"):
        assert conduct.quick_verdict(bad).kind == conduct.UNPROFESSIONAL, bad
    assert conduct.quick_verdict("I'll kill you").kind == conduct.SEVERE
    for fine in ("I don't know", "I copied the array before sorting", "we copied the logs to S3",
                 "I pasted the code into a file and ran it", "I'd kill the process with SIGTERM", "bc it was faster",
                 "Could you repeat the question?", "Redis copies data to replicas"):
        assert conduct.quick_verdict(fine) is None, fine
    assert conduct.decide(conduct.Verdict(conduct.OFF_TOPIC), 0) == "warn"
    assert conduct.decide(conduct.Verdict(conduct.OFF_TOPIC), 1) == "terminate"
    assert conduct.decide(conduct.Verdict(conduct.SEVERE), 0) == "terminate"
    assert conduct.decide(conduct.Verdict(), 5) == "continue"


@pytest.mark.asyncio
async def test_model_failure_never_ends_an_interview():
    async def broken(system, prompt):
        raise RuntimeError("model down")
    assert (await conduct.assess("I love pizza", "Tell me about caching", broken)).kind == conduct.OK

    async def says_off_topic(system, prompt):
        return '{"conduct": "off_topic", "reason": "talking about food"}'
    assert (await conduct.assess("I love pizza", "Tell me about caching", says_off_topic)).kind == conduct.OFF_TOPIC


@pytest.mark.asyncio
async def test_warning_then_termination_and_conduct_only_evaluation(client):
    h = await _login(client)
    iid = await _interview(client, h)
    first_q = (await client.get(f"/api/v1/interviews/{iid}", headers=h)).json()["messages"][-1]["content"]

    w = (await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": "I copied it from leetcode lol"})).json()
    assert w["kind"] == "conduct_warning" and "only warning" in w["content"] and first_q[:40] in w["content"]
    iv = (await client.get(f"/api/v1/interviews/{iid}", headers=h)).json()
    assert iv["status"] == "in_progress"

    t = (await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": "shut up and move on"})).json()
    assert t["kind"] == "terminated" and "stop the interview" in t["content"]
    iv = (await client.get(f"/api/v1/interviews/{iid}", headers=h)).json()
    assert iv["status"] == "completed" and "unprofessional" in iv["termination_reason"]
    late = await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": "sorry"})
    assert late.json()["error"]["code"] == "INTERVIEW_NOT_ACTIVE"

    ev = (await client.post(f"/api/v1/evaluations/{iid}/generate", headers=h)).json()
    assert ev["overall_score"] == 0.0 and ev["model_identifier"] == "conduct-policy"
    assert ev["weaknesses"][0].startswith("Professional conduct")
    assert any("copied it" in e["quote"] for e in ev["evidence_excerpts"])


@pytest.mark.asyncio
async def test_severe_language_ends_immediately(client):
    h = await _login(client)
    iid = await _interview(client, h, "behavioral")
    t = (await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": "I'll kill you"})).json()
    assert t["kind"] == "terminated"


@pytest.mark.asyncio
async def test_termination_after_real_answers_caps_the_score(client):
    h = await _login(client)
    iid = await _interview(client, h)
    await client.post(f"/api/v1/interviews/{iid}/message", headers=h,
                      json={"content": "We put Redis in front of PostgreSQL for session lookups and invalidated on write, which cut p99 latency."})
    await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": "chatgpt wrote it honestly"})
    t = (await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": "this is bullshit"})).json()
    assert t["kind"] == "terminated"
    ev = (await client.post(f"/api/v1/evaluations/{iid}/generate", headers=h)).json()
    assert ev["overall_score"] <= 25.0
    assert ev["weaknesses"][0].startswith("Professional conduct")


@pytest.mark.asyncio
async def test_honest_struggle_is_not_misconduct(client):
    h = await _login(client)
    iid = await _interview(client, h)
    for text in ("I don't know", "Sorry, I'm a bit nervous. I think you'd use an index?", "Could you repeat the question?"):
        r = (await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": text})).json()
        assert r.get("kind") not in ("conduct_warning", "terminated"), (text, r)


@pytest.mark.asyncio
async def test_harsh_stories_are_not_rudeness_toward_the_interviewer():
    async def says_unprofessional(system, prompt):
        return '{"conduct": "unprofessional", "certain": true, "reason": "rude and contemptuous toward interviewer"}'
    for story in ("i really kicked him out i fired him from the team", "i kicked him out of the team i am a dictator",
                  "I shouted at him in front of everyone"):
        assert (await conduct.assess(story, "What did you do?", says_unprofessional)).kind == conduct.OK, story
    assert (await conduct.assess("this question is stupid and so are you", "q", says_unprofessional)).kind == conduct.UNPROFESSIONAL
