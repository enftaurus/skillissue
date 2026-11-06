import uuid

import pytest

from backend.app.database.models import ProjectSubmission


async def _login(client):
    email = f"rep_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    tok = (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
    me = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})).json()
    return {"Authorization": f"Bearer {tok}"}, me["id"]


@pytest.mark.asyncio
async def test_reports_list_and_project_report_are_user_scoped(client, db_session):
    h, uid = await _login(client)
    other, _ = await _login(client)
    sub = ProjectSubmission(user_id=uid, project_id="distributed-rate-limiter", status="passed",
                            test_results={"passed_tests": 5, "total_tests": 6}, prompts_count=4,
                            prompt_analysis={"overall_score": 72, "grade": "B", "summary": "ok", "evaluated_prompts": [],
                                             "key_takeaways": [], "rubric_breakdown": {}})
    db_session.add(sub)
    await db_session.commit()
    mine = (await client.get("/api/v1/reports", headers=h)).json()
    r = next(x for x in mine if x["kind"] == "ai_prompt")
    assert r["score"] == 72 and r["link"] == f"/reports/projects/{sub.id}" and "5/6 tests" in r["subtitle"]
    assert (await client.get(f"/api/v1/reports/projects/{sub.id}", headers=h)).json()["prompt_analysis"]["grade"] == "B"
    assert all(x["id"] != sub.id for x in (await client.get("/api/v1/reports", headers=other)).json())
    assert (await client.get(f"/api/v1/reports/projects/{sub.id}", headers=other)).status_code == 404
