import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_company_tracks_day_1_open(client: AsyncClient):
    # Register and login user
    email = f"track_user_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch company tracks catalog
    res = await client.get("/api/v1/tracks/companies", headers=headers)
    assert res.status_code == 200
    tracks = res.json()
    assert len(tracks) >= 8

    # Verify Gold, Silver, and Bronze mines exist
    tiers = {t["tier"] for t in tracks}
    assert "gold" in tiers
    assert "silver" in tiers
    assert "bronze" in tiers

    # Verify Uber track details
    uber_track = next((t for t in tracks if t["slug"] == "uber"), None)
    assert uber_track is not None
    assert uber_track["tier"] == "gold"
    assert uber_track["unlocked_count"] >= 3
    assert len(uber_track["community_tips"]) > 0

    # 2. Get Uber track details
    uber_detail_res = await client.get("/api/v1/tracks/companies/uber", headers=headers)
    assert uber_detail_res.status_code == 200
    uber_detail = uber_detail_res.json()
    assert len(uber_detail["problems"]) >= 3

    # Verify first 3 problems are UNLOCKED from Day 1
    unlocked_problems = [p for p in uber_detail["problems"] if p["is_unlocked"]]
    assert len(unlocked_problems) >= 3

    # Check a specific Day-1 unlocked problem
    p1 = unlocked_problems[0]
    prob_res = await client.get(f"/api/v1/tracks/problems/{p1['id']}", headers=headers)
    assert prob_res.status_code == 200
    p_data = prob_res.json()
    assert p_data["is_unlocked"] is True
    assert "description" in p_data
    assert "python" in p_data["starter_code"]
