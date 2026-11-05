import shutil
import uuid

import pytest

from backend.app.projects.process import process_flags, verification_metrics
from backend.app.projects.repository import PROJECTS_CATALOG
from backend.app.projects.service import ProjectService

needs_bwrap = pytest.mark.skipif(not shutil.which("bwrap"), reason="bubblewrap not installed")


@needs_bwrap
@pytest.mark.parametrize("pid", ["idempotent-payments", "webhook-signatures"])
def test_template_projects_are_solvable_and_starter_fails(pid):
    p = PROJECTS_CATALOG[pid]
    starter = ProjectService.run_tests_in_sandbox(pid, {})
    solved = ProjectService.run_tests_in_sandbox(pid, p["reference_solution"])
    assert starter.status == "failed" and starter.passed_tests < starter.total_tests
    assert solved.status == "passed" and solved.passed_tests == solved.total_tests, solved.raw_output[-800:]


def test_reference_solutions_never_leak():
    from backend.app.projects.repository import get_project
    for pid in ("idempotent-payments", "webhook-signatures"):
        assert "reference_solution" not in get_project(pid).model_dump()


def test_verification_metrics():
    tl = [{"kind": "prompt"}, {"kind": "test_run", "status": "failed"}, {"kind": "prompt"}, {"kind": "submit", "status": "passed"}]
    m = verification_metrics(tl)
    assert m["verification_rate"] == 0.5 and m["verified_replies"] == 1 and m["test_runs"] == 1
    assert process_flags(m) == []  # half verified isn't flagged
    m3 = verification_metrics([{"kind": "prompt"}, {"kind": "test_run"}, {"kind": "prompt"}, {"kind": "prompt"}])
    assert m3["verification_rate"] == 0.33 and process_flags(m3)
    assert verification_metrics([{"kind": "submit"}])["submitted_without_running_tests"]


@needs_bwrap
@pytest.mark.asyncio
async def test_submit_reports_verification_from_server_events(client):
    email = f"proc_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    h = {"Authorization": "Bearer " + (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]}
    pid = "webhook-signatures"
    sol = PROJECTS_CATALOG[pid]["reference_solution"]
    await client.post(f"/api/v1/projects/{pid}/copilot", headers=h, json={"files": {}, "message": "In src/webhooks.py how should I parse the t= field?"})
    assert (await client.post(f"/api/v1/projects/{pid}/run-tests", headers=h, json={"files": {}})).status_code == 200
    await client.post(f"/api/v1/projects/{pid}/copilot", headers=h, json={"files": {}, "message": "Does hmac.compare_digest work on hex strings?"})
    tl = (await client.get(f"/api/v1/projects/{pid}/timeline", headers=h)).json()
    assert [e["kind"] for e in tl["timeline"]] == ["prompt", "test_run", "prompt"]
    r = await client.post(f"/api/v1/projects/{pid}/submit", headers=h, json={"files": sol, "time_spent_seconds": 600})
    assert r.status_code == 201, r.text
    proc = r.json()["prompt_analysis"]["process"]
    assert proc["prompts"] == 2 and proc["verification_rate"] == 0.5 and proc["submitted_green"]
