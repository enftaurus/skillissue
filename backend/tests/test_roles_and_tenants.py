import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_role_and_test_self_assignment_ignored(client: AsyncClient):
    """
    D1: Sending role=admin or is_test=true in public register payload
    must be ignored and still yield a plain role=candidate, is_test=False.
    """
    cand_email = f"attacker_{uuid.uuid4().hex[:6]}@domain.com"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": cand_email,
            "password": "Password123!",
            "role": "admin",
            "is_test": True
        }
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["role"] == "candidate"
    assert user_data["is_test"] is False

    # Log in and verify returned token
    login_res = await client.post("/api/v1/auth/login", json={"email": cand_email, "password": "Password123!"})
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert token_data["role"] == "candidate"
    assert token_data["is_test"] is False

    # Attempting to access admin endpoint with this token must yield 403
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    admin_res = await client.get("/api/v1/analytics/admin/stats", headers=headers)
    assert admin_res.status_code == 403

@pytest.mark.asyncio
async def test_recruiter_registration_creates_tenant_and_user(client: AsyncClient):
    """
    D1: POST /auth/register-recruiter provisions an organisation tenant and recruiter user.
    """
    recruiter_email = f"recruiter_{uuid.uuid4().hex[:6]}@hiringcorp.com"
    org_name = f"Hiring Corp {uuid.uuid4().hex[:4]}"
    reg_res = await client.post(
        "/api/v1/auth/register-recruiter",
        json={
            "organisation_name": org_name,
            "email": recruiter_email,
            "password": "SecurePassword123!"
        }
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["role"] == "recruiter"
    assert user_data["tenant_id"] is not None
    assert user_data["tenant_id"] != "tenant-prod-default"
    assert user_data["is_test"] is False

    # Log in as recruiter
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": recruiter_email, "password": "SecurePassword123!"}
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert token_data["role"] == "recruiter"
    assert token_data["tenant_id"] == user_data["tenant_id"]

@pytest.mark.asyncio
async def test_candidate_forbidden_from_admin_analytics(client: AsyncClient):
    # Candidate user
    cand_email = f"cand_{uuid.uuid4().hex[:6]}@domain.com"
    await client.post("/api/v1/auth/register", json={"email": cand_email, "password": "Password123!"})
    login_res = await client.post("/api/v1/auth/login", json={"email": cand_email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to access admin telemetry
    admin_res = await client.get("/api/v1/analytics/admin/stats", headers=headers)
    assert admin_res.status_code == 403

@pytest.mark.asyncio
async def test_admin_analytics_real_vs_test_partitioning(client: AsyncClient, create_test_user):
    # D1: Admins are created directly in DB via test fixture, not over HTTP
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@skillissue.com"
    await create_test_user(email=admin_email, password="Password123!", role="admin")

    login_res = await client.post("/api/v1/auth/login", json={"email": admin_email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Admin accesses tenant telemetry
    admin_res = await client.get("/api/v1/analytics/admin/stats", headers=headers)
    assert admin_res.status_code == 200
    data = admin_res.json()

    assert "real_stats" in data
    assert "test_stats" in data
    assert "tenants" in data
    assert "user_count" in data["real_stats"]
    assert "user_count" in data["test_stats"]
    assert len(data["tenants"]) >= 1

@pytest.mark.asyncio
async def test_company_tracks_and_placement_simulations(client: AsyncClient):
    # Candidate accesses tracks and simulations
    cand_email = f"cand2_{uuid.uuid4().hex[:6]}@domain.com"
    await client.post("/api/v1/auth/register", json={"email": cand_email, "password": "Password123!"})
    login_res = await client.post("/api/v1/auth/login", json={"email": cand_email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 50+ company tracks
    tracks_res = await client.get("/api/v1/tracks/companies", headers=headers)
    assert tracks_res.status_code == 200
    tracks = tracks_res.json()
    assert len(tracks) >= 50
    # Day-1 unlock condition
    for t in tracks:
        assert t["unlocked_count"] >= 2

    # 2. Placement Simulations
    sims_res = await client.get("/api/v1/tracks/simulations", headers=headers)
    assert sims_res.status_code == 200
    sims = sims_res.json()
    assert len(sims) == 3
    companies = [s["company"] for s in sims]
    assert "Google" in companies
    assert "Uber" in companies
    assert "OpenAI" in companies
