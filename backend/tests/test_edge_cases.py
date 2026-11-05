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


# --- second sweep (2026-11-06, E9-E13 in docs/reports/qa-audit-2026-11-05.md)-------------------------------------------------------

@pytest.mark.asyncio
async def test_nul_in_query_or_path_is_400_not_500(client):
    h = await _login(client)
    r = await client.get("/api/v1/learning-backlog", headers=h, params={"topic": "a\x00b"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_CHARACTERS"
    r = await client.get("/api/v1/job-descriptions/a%00b", headers=h)
    assert r.status_code == 400
    r = await client.get("/api/v1/learning-backlog", headers=h, params={"topic": "cache"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_backlog_and_jd_text_bounds(client):
    h = await _login(client)
    for body in ({"topic": "Caching", "notes": "n" * 2_000_000},
                 {"topic": "Caching", "source_id": "x" * 37},
                 {"topic": "Caching", "reason": "r" * 5000}):
        r = await client.post("/api/v1/learning-backlog", headers=h, json=body)
        assert r.status_code == 422, list(body)
    r = await client.post("/api/v1/learning-backlog/queue-weakness", headers=h, json={"topic": "x", "interview_id": "i" * 40})
    assert r.status_code == 422
    r = await client.post("/api/v1/job-descriptions", headers=h, json={"title": "Big", "raw_text": "x" * 60_000})
    assert r.status_code == 422
    r = await client.post("/api/v1/job-descriptions", headers=h, json={"title": "Co", "company": "c" * 201, "raw_text": "Python " * 10})
    assert r.status_code == 422  # String(200) column: used to be a DataError 500
    r = await client.post("/api/v1/job-descriptions", headers=h, json={"title": "Backend", "raw_text": "Python FastAPI " * 10})
    assert r.status_code in (200, 201), r.text
    jid = r.json()["id"]
    for body in ({"extracted_skills": ["s"] * 101}, {"title": "t" * 201}, {"extracted_role": "r" * 201}):
        assert (await client.put(f"/api/v1/job-descriptions/{jid}", headers=h, json=body)).status_code == 422


@pytest.mark.asyncio
async def test_jd_model_output_is_clamped(client, monkeypatch):
    from types import SimpleNamespace
    from backend.app.providers.factory import ModelFactory

    class _Fake:
        async def generate_json(self, prompt, system_prompt=None, **kw):
            return SimpleNamespace(content="{}", parsed_json={"role": "R" * 500, "extracted_skills": ["s" * 300] * 500,
                                                          "extracted_requirements": "not a list"})

    async def _get(*a, **k):
        return _Fake()

    monkeypatch.setattr(ModelFactory, "get_for_user", _get)
    h = await _login(client)
    r = await client.post("/api/v1/job-descriptions", headers=h, json={"title": "Backend", "raw_text": "Python FastAPI " * 10})
    assert r.status_code in (200, 201), r.text
    jd = r.json()
    assert len(jd["extracted_role"]) == 200 and len(jd["extracted_skills"]) == 100
    assert all(len(s) <= 200 for s in jd["extracted_skills"]) and jd["extracted_requirements"] == []


@pytest.mark.asyncio
async def test_concurrent_queue_weakness_stores_one_row(db_session):
    """4 parallel 'queue for later' clicks used to store 4 rows (dedupe SELECT raced)."""
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool
    from backend.app.core.config import settings
    from backend.app.database.session import get_db

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _own_session():  # one session per request, like production
        async with maker() as s:
            yield s
            await s.commit()

    app = create_application()
    app.dependency_overrides[get_db] = _own_session
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            h = await _login(c)
            rs = await asyncio.gather(*[c.post("/api/v1/learning-backlog/queue-weakness", headers=h,
                                               json={"topic": "Race topic"}) for _ in range(4)])
            assert all(r.status_code == 200 for r in rs), [r.text for r in rs]
            assert len({r.json()["id"] for r in rs}) == 1
            assert sum(r.json()["is_existing"] for r in rs) == 3
            # Rows duplicated before the fix must not turn dedupe into a MultipleResultsFound 500.
            await c.post("/api/v1/learning-backlog", headers=h, json={"topic": "Race topic"})
            r = await c.post("/api/v1/learning-backlog/queue-weakness", headers=h, json={"topic": "race topic"})
            assert r.status_code == 200 and r.json()["is_existing"]
    finally:
        await engine.dispose()
