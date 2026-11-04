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
    assert "leetcode_url" in p_data
    assert p_data["leetcode_url"].startswith("https://leetcode.com/problems/")

    # 3. Verify leetcode_url is exposed for unlocked problems, but hidden for locked problems
    for prob in uber_detail["problems"]:
        assert "leetcode_url" in prob
        if prob["is_unlocked"]:
            assert prob["leetcode_url"].startswith("https://leetcode.com/problems/")
        else:
            assert prob["leetcode_url"] == ""

    # 4. Toggle problem solved on LeetCode
    toggle_res = await client.post(f"/api/v1/tracks/problems/{p1['id']}/toggle-solved", headers=headers)
    assert toggle_res.status_code == 200
    toggle_data = toggle_res.json()
    assert toggle_data["is_solved"] is True
    assert toggle_data["solved_count"] == 1
    assert toggle_data["unlocked_new_problem"] is True
    assert toggle_data["unlocked_count"] == 4

    # 5. Verify Uber track detail reflects newly unlocked 4th question
    updated_uber = (await client.get("/api/v1/tracks/companies/uber", headers=headers)).json()
    assert updated_uber["solved_count"] == 1
    assert updated_uber["unlocked_count"] == 4
    unlocked_after = [p for p in updated_uber["problems"] if p["is_unlocked"]]
    assert len(unlocked_after) == 4
    p1_after = next(p for p in updated_uber["problems"] if p["id"] == p1["id"])
    assert p1_after["is_solved"] is True

