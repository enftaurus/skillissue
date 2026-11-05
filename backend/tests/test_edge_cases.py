"""Regression tests from the 2026-11-06 edge-case probe (scripts/evals/edge_probe.py)."""
import uuid

import httpx
import pytest

from backend.app.coding.problems import get_problem
from backend.app.coding.service import sanitize_test_result_dict
from backend.app.core.errors import AppException
from backend.app.main import create_application


@pytest.mark.asyncio
async def test_error_envelopes():
    app = create_application()

    @app.get("/_t/details")
    async def _details():
        raise AppException("Set up Bedrock first.", code="BEDROCK_CONFIG_REQUIRED", details={"setup_url": "/onboarding/bedrock"})

    @app.get("/_t/boom")
    async def _boom():
        raise RuntimeError("secret internal path /home/x")

    @app.post("/_t/validate")
    async def _validate(body: dict[str, int]):
        return body

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/_t/details")
        assert r.status_code == 400  # used to be a TypeError -> 500 for every user without a provider
        assert r.json()["error"]["details"]["setup_url"] == "/onboarding/bedrock"
        r = await c.get("/_t/boom")
        assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR" and "/home/x" not in r.text
        r = await c.post("/_t/validate", json={"a": "x" * 50_000})
        assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
        assert len(r.text) < 2000  # rejected input is not echoed back


async def _login(client):
    email = f"edge_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    tok = (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest.mark.asyncio
async def test_nul_bytes_in_answers_are_stripped_not_500(client):
    h = await _login(client)
    iid = (await client.post("/api/v1/interviews/domain", headers=h, json={"category": "technical", "domain_skills": ["Python"]})).json()["id"]
    r = await client.post(f"/api/v1/interviews/{iid}/message", headers=h,
                          json={"content": "I used \x00 Redis ‮ for sessions.", "client_turn_id": str(uuid.uuid4())})
    assert r.status_code == 200, r.text
    msgs = (await client.get(f"/api/v1/interviews/{iid}", headers=h)).json()["messages"]
    assert any(m["role"] == "user" and "\x00" not in m["content"] and "Redis" in m["content"] for m in msgs)
    r = await client.post(f"/api/v1/interviews/{iid}/message", headers=h, json={"content": "\x00\x00"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "EMPTY_ANSWER"


def test_unknown_problem_is_not_silently_two_sum():
    assert get_problem("definitely-not-a-problem") is None
    assert get_problem("two-sum") is not None


def test_failed_tests_are_not_labelled_passed():
    assert sanitize_test_result_dict({"passed": False})["status"] == "failed"
    assert sanitize_test_result_dict({"passed": True})["status"] == "passed"


@pytest.mark.asyncio
async def test_project_and_copilot_size_limits(client):
    h = await _login(client)
    r = await client.post("/api/v1/projects/async-job-queue/run-tests", headers=h, json={"files": {"src/dispatcher.py": "#" * 300_000}})
    assert r.status_code == 422
    r = await client.post("/api/v1/projects/async-job-queue/copilot", headers=h, json={"files": {}, "message": "x" * 5000})
    assert r.status_code == 422
    r = await client.post("/api/v1/coding/run", headers=h, json={"problem_id": "nope-123", "language": "python", "code": "print(1)"})
    assert r.status_code == 404
