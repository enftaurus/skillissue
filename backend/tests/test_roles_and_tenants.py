import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_candidate_forbidden_from_admin_analytics(client: AsyncClient):
    # Candidate user
    cand_email = f"cand_{uuid.uuid4().hex[:6]}@domain.com"
    await client.post("/api/v1/auth/register", json={"email": cand_email, "password": "Password123!", "role": "candidate"})
    login_res = await client.post("/api/v1/auth/login", json={"email": cand_email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to access admin telemetry
    admin_res = await client.get("/api/v1/analytics/admin/stats", headers=headers)
    assert admin_res.status_code == 403

@pytest.mark.asyncio
async def test_admin_analytics_real_vs_test_partitioning(client: AsyncClient):
    # Admin user
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@skillissue.com"
    await client.post("/api/v1/auth/register", json={"email": admin_email, "password": "Password123!", "role": "admin"})
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
    assert len(data["tenants"]) >= 2

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
