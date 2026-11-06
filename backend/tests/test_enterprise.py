import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_enterprise_pipeline_candidate_entry_and_scoring(client: AsyncClient):
    # 1. Register recruiter via dedicated recruiter registration
    email = f"recruiter_{uuid.uuid4().hex[:8]}@acme.corp"
    reg_res = await client.post(
        "/api/v1/auth/register-recruiter",
        json={"organisation_name": "Acme Corp", "email": email, "password": "Password123!"}
    )
    assert reg_res.status_code == 201
    recruiter_data = reg_res.json()
    tenant_a_id = recruiter_data["tenant_id"]

    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Assessment Pipeline
    pipeline_payload = {
        "title": "Uber SDE-1 Campus Hiring Assessment 2026",
        "target_role": "Backend Engineer",
        "job_description": "We are seeking talented SDE-1 engineers proficient in distributed systems, concurrency, and clean API design.",
        "rounds": [
            {
                "round_type": "oa_dsa",
                "name": "Round 1: Company DSA OA",
                "time_limit_minutes": 35,
                "is_enabled": True,
                "config": {"topics": ["Array", "Graph"]}
            },
            {
                "round_type": "ai_project",
                "name": "Round 2: Machine Coding Take-Home",
                "time_limit_minutes": 30,
                "is_enabled": True,
                "config": {"project_id": "distributed-rate-limiter"}
            },
            {
                "round_type": "tough_interview",
                "name": "Round 3: Anti-Sycophancy AI Interview",
                "time_limit_minutes": 20,
                "is_enabled": True,
                "config": {"questions": 4}
            }
        ]
    }
    create_res = await client.post("/api/v1/enterprise/pipelines", headers=headers, json=pipeline_payload)
    assert create_res.status_code == 201
    pipe_data = create_res.json()
    assert pipe_data["title"] == "Uber SDE-1 Campus Hiring Assessment 2026"
    assert pipe_data["tenant_id"] == tenant_a_id
    assert len(pipe_data["rounds"]) == 3
    pipe_id = pipe_data["id"]
    invite_token = pipe_data["invite_token"]

    # 3. Viewing the invite token is public landing info only and never creates a candidate
    invite_view_res = await client.get(f"/api/v1/enterprise/assessments/{invite_token}")
    assert invite_view_res.status_code == 200
    invite_view_data = invite_view_res.json()
    assert invite_view_data["status"] == "entry_required"
    assert invite_view_data["requires_login"] is True
    assert invite_view_data["access_token"] == ""

    # 4. Entry needs a signed-in candidate account (ADR 0027); anonymous name+email entry is gone
    anon = await client.post(f"/api/v1/enterprise/assessments/entry/{invite_token}",
                             json={"candidate_name": "Alice Candidate", "candidate_email": "alice@university.edu"})
    assert anon.status_code == 401
    alice_email = f"alice_{uuid.uuid4().hex[:6]}@university.edu"
    await client.post("/api/v1/auth/register", json={"email": alice_email, "password": "Password123!"})
    alice_tok = (await client.post("/api/v1/auth/login", json={"email": alice_email, "password": "Password123!"})).json()["access_token"]
    alice = {"Authorization": f"Bearer {alice_tok}"}
    entry_res = await client.post(f"/api/v1/enterprise/assessments/entry/{invite_token}", headers=alice,
                                  json={"candidate_name": "Alice Candidate", "candidate_email": "spoof@evil.com"})
    assert entry_res.status_code == 201
    entry_data = entry_res.json()
    access_token = entry_data["access_token"]
    assert access_token != ""
    assert entry_data["candidate_name"] == "Alice Candidate"
    assert entry_data["candidate_email"] == alice_email  # identity comes from the account, not the body
    assert "round_results" not in entry_data and "composite_score" not in entry_data

    re_entry = await client.post(f"/api/v1/enterprise/assessments/entry/{invite_token}", headers=alice, json={})
    assert re_entry.status_code == 201
    assert re_entry.json()["id"] == entry_data["id"]

    # 5. Client-supplied scores are ignored and the response never carries results
    sub1_res = await client.post(
        f"/api/v1/enterprise/assessments/{access_token}/submit-round", headers=alice,
        json={"round_index": 0, "round_type": "oa_dsa",
              "submission_data": {"score": 100.0, "code": "def solve(): return 1"},
              "integrity_events": {"window_blurs": 5, "copy_paste_count": 10}}
    )
    assert sub1_res.status_code == 200
    sub1_data = sub1_res.json()
    assert sub1_data["current_round_index"] == 1
    assert sub1_data["status"] == "in_progress"
    for leaked in ("round_results", "composite_score", "integrity_signals"):
        assert leaked not in sub1_data

    for idx, rtype in ((1, "ai_project"), (2, "tough_interview")):
        r = await client.post(f"/api/v1/enterprise/assessments/{access_token}/submit-round", headers=alice,
                              json={"round_index": idx, "round_type": rtype, "submission_data": {"score": 99.0}})
        assert r.status_code == 200
    assert r.json()["status"] == "completed"

    # 6. Recruiter leaderboard: the unattempted DSA round scored 0 server-side, not the client's 100
    lb_res = await client.get(f"/api/v1/enterprise/pipelines/{pipe_id}/leaderboard", headers=headers)
    assert lb_res.status_code == 200
    lb_data = lb_res.json()
    assert lb_data["total_candidates"] == 1
    assert lb_data["completed_candidates"] == 1
    cand = lb_data["candidates"][0]
    assert cand["candidate_name"] == "Alice Candidate"
    assert cand["access_token"] == ""
    assert cand["round_results"]["0"]["score"] == 0.0
    assert cand["composite_score"] is not None and cand["composite_score"] < 50
    assert lb_data["rankings"][0]["rank"] == 1

@pytest.mark.asyncio
async def test_tenant_isolation_on_pipelines(client: AsyncClient, create_test_user):
    """
    D5: Strict tenant isolation tests.
    - Recruiter in Tenant B cannot read, edit, export, or view leaderboard of Tenant A's pipeline.
    - Recruiter B cannot see Tenant A's pipeline in the pipeline list.
    - Recruiter A2 in Tenant A can see and manage Tenant A's pipeline.
    - Admin can see all pipelines.
    """
    # 1. Create Recruiter A in Tenant A
    rec_a_email = f"rec_a_{uuid.uuid4().hex[:6]}@org-alpha.com"
    reg_a = await client.post(
        "/api/v1/auth/register-recruiter",
        json={"organisation_name": "Org Alpha", "email": rec_a_email, "password": "Password123!"}
    )
    assert reg_a.status_code == 201
    tenant_a_id = reg_a.json()["tenant_id"]

    login_a = await client.post("/api/v1/auth/login", json={"email": rec_a_email, "password": "Password123!"})
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Recruiter A creates a pipeline
    pipe_res = await client.post(
        "/api/v1/enterprise/pipelines",
        headers=headers_a,
        json={
            "title": "Alpha Confidential SDE Hiring",
            "target_role": "Core Systems",
            "job_description": "Building confidential high-frequency core systems."
        }
    )
    assert pipe_res.status_code == 201
    pipe_a_id = pipe_res.json()["id"]

    # 2. Create Recruiter B in Tenant B
    rec_b_email = f"rec_b_{uuid.uuid4().hex[:6]}@org-beta.com"
    reg_b = await client.post(
        "/api/v1/auth/register-recruiter",
        json={"organisation_name": "Org Beta", "email": rec_b_email, "password": "Password123!"}
    )
    assert reg_b.status_code == 201
    tenant_b_id = reg_b.json()["tenant_id"]
    assert tenant_b_id != tenant_a_id

    login_b = await client.post("/api/v1/auth/login", json={"email": rec_b_email, "password": "Password123!"})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Recruiter B attempts to view Recruiter A's pipeline -> 403 Forbidden
    get_res = await client.get(f"/api/v1/enterprise/pipelines/{pipe_a_id}", headers=headers_b)
    assert get_res.status_code == 403

    # Recruiter B attempts to edit Recruiter A's pipeline -> 403 Forbidden
    put_res = await client.put(
        f"/api/v1/enterprise/pipelines/{pipe_a_id}",
        headers=headers_b,
        json={"title": "Hacked Pipeline"}
    )
    assert put_res.status_code == 403

    # Recruiter B attempts to invite to Recruiter A's pipeline -> 403 Forbidden
    inv_res = await client.post(
        f"/api/v1/enterprise/pipelines/{pipe_a_id}/invite",
        headers=headers_b,
        json={"candidate_name": "Eve", "candidate_email": "eve@evil.corp"}
    )
    assert inv_res.status_code == 403

    # Recruiter B attempts to view leaderboard of Recruiter A's pipeline -> 403 Forbidden
    lb_res = await client.get(f"/api/v1/enterprise/pipelines/{pipe_a_id}/leaderboard", headers=headers_b)
    assert lb_res.status_code == 403

    # Recruiter B attempts to export Recruiter A's pipeline -> 403 Forbidden
    exp_res = await client.get(f"/api/v1/enterprise/pipelines/{pipe_a_id}/export", headers=headers_b)
    assert exp_res.status_code == 403

    # Recruiter B lists pipelines -> Tenant A's pipeline must NOT be present
    list_b = await client.get("/api/v1/enterprise/pipelines", headers=headers_b)
    assert list_b.status_code == 200
    b_pipe_ids = [p["id"] for p in list_b.json()]
    assert pipe_a_id not in b_pipe_ids

    # 3. Second recruiter in Tenant A (same tenant) CAN see and access Tenant A's pipeline
    rec_a2_email = f"rec_a2_{uuid.uuid4().hex[:6]}@org-alpha.com"
    await create_test_user(email=rec_a2_email, role="recruiter", tenant_id=tenant_a_id)
    login_a2 = await client.post("/api/v1/auth/login", json={"email": rec_a2_email, "password": "Password123!"})
    token_a2 = login_a2.json()["access_token"]
    headers_a2 = {"Authorization": f"Bearer {token_a2}"}

    get_a2 = await client.get(f"/api/v1/enterprise/pipelines/{pipe_a_id}", headers=headers_a2)
    assert get_a2.status_code == 200
    assert get_a2.json()["title"] == "Alpha Confidential SDE Hiring"

    list_a2 = await client.get("/api/v1/enterprise/pipelines", headers=headers_a2)
    assert list_a2.status_code == 200
    assert pipe_a_id in [p["id"] for p in list_a2.json()]

    # 4. Admin user CAN see and access all pipelines
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@skillissue.com"
    await create_test_user(email=admin_email, role="admin", tenant_id="tenant-prod-default")
    login_adm = await client.post("/api/v1/auth/login", json={"email": admin_email, "password": "Password123!"})
    token_adm = login_adm.json()["access_token"]
    headers_adm = {"Authorization": f"Bearer {token_adm}"}

    get_adm = await client.get(f"/api/v1/enterprise/pipelines/{pipe_a_id}", headers=headers_adm)
    assert get_adm.status_code == 200
    assert get_adm.json()["title"] == "Alpha Confidential SDE Hiring"
