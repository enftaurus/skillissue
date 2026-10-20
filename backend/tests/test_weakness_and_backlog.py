import uuid
import pytest
import httpx

@pytest.mark.asyncio
async def test_weakness_analysis_and_backlog_flow(client: httpx.AsyncClient):
    # 1. Register candidate and login
    email = f"backlog_user_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!"}
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Queue a weakness manually or from evaluation
    queue_res = await client.post(
        "/api/v1/learning-backlog/queue-weakness",
        headers=headers,
        json={
            "topic": "Distributed Locking",
            "subtopic": "Redis Redlock vs Postgres advisory locks",
            "reason": "Struggled to explain split-brain scenarios in distributed locking during system design interview.",
            "learning_objective": "Understand consensus vs lease-based locks and trade-offs.",
            "suggested_exercise": "Implement a distributed lock with automatic heartbeat renewal.",
            "priority": "high",
            "notes": "Review Martin Kleppmann's critique of Redlock."
        }
    )
    assert queue_res.status_code == 200
    item = queue_res.json()
    assert item["topic"] == "Distributed Locking"
    assert item["status"] == "queued"
    assert item["priority"] == "high"
    assert item["is_existing"] is False
    item_id = item["id"]

    # 3. Duplicate queueing should update context and return is_existing: True
    queue_dup = await client.post(
        "/api/v1/learning-backlog/queue-weakness",
        headers=headers,
        json={
            "topic": "Distributed Locking",
            "subtopic": "Consensus trade-offs",
            "reason": "Second interview also revealed weak understanding.",
            "priority": "high"
        }
    )
    assert queue_dup.status_code == 200
    dup_item = queue_dup.json()
    assert dup_item["id"] == item_id
    assert dup_item["is_existing"] is True
    assert dup_item["priority"] == "high"

    # 4. List backlog items
    backlog_list = await client.get("/api/v1/learning-backlog", headers=headers)
    assert backlog_list.status_code == 200
    items = backlog_list.json()
    assert len(items) == 1
    assert items[0]["id"] == item_id

    # 5. Patch backlog item
    patch_res = await client.patch(
        f"/api/v1/learning-backlog/{item_id}",
        headers=headers,
        json={"notes": "Updated research notes", "priority": "medium"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["notes"] == "Updated research notes"
    assert patch_res.json()["priority"] == "medium"

    # 6. Create custom plan (Planly)
    plan_create = await client.post(
        "/api/v1/plans/custom",
        headers=headers,
        json={
            "topic": "Backend Reliability",
            "goal": "interview_prep",
            "daily_study_minutes": 45,
            "schedule_days": ["monday", "wednesday", "friday"],
            "current_level": "intermediate"
        }
    )
    assert plan_create.status_code == 201
    plan = plan_create.json()
    plan_id = plan["id"]

    # 7. Get suggested backlog items for this plan
    suggested = await client.get(f"/api/v1/plans/{plan_id}/suggested-backlog", headers=headers)
    assert suggested.status_code == 200
    sugg_items = suggested.json()
    assert len(sugg_items) >= 1
    assert any(s["id"] == item_id for s in sugg_items)

    # 8. Deliberately import backlog item into the plan
    import_res = await client.post(
        f"/api/v1/plans/{plan_id}/backlog-items",
        headers=headers,
        json={"backlog_item_ids": [item_id]}
    )
    assert import_res.status_code == 200
    updated_plan = import_res.json()
    # Check that a task was added with the topic
    assert any("Distributed Locking" in (t.get("subtopic") or "") or "Distributed Locking" in t["title"] for t in updated_plan["tasks"])

    # 9. Verify backlog item is now 'planned'
    backlog_after = await client.get("/api/v1/learning-backlog", headers=headers)
    assert backlog_after.status_code == 200
    updated_item = next(i for i in backlog_after.json() if i["id"] == item_id)
    assert updated_item["status"] == "planned"
    assert updated_item["planned_plan_id"] == plan_id

    # 10. Delete backlog item
    del_res = await client.delete(f"/api/v1/learning-backlog/{item_id}", headers=headers)
    assert del_res.status_code == 204

@pytest.mark.asyncio
async def test_dsa_arena_coaching_agent(client: httpx.AsyncClient):
    # 1. Register candidate and login
    email = f"dsa_user_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get two-sum problem
    prob_res = await client.get("/api/v1/coding/problems/two-sum", headers=headers)
    assert prob_res.status_code == 200
    prob = prob_res.json()
    assert prob["ai_coaching_supported"] is True

    # 3. Request Level 1 hint
    hint1_res = await client.post(
        "/api/v1/coding/problems/two-sum/coach",
        headers=headers,
        json={
            "user_code": "def twoSum(nums, target):\n    # not sure how to optimize beyond O(N^2)\n    pass",
            "language": "python",
            "hint_level": 1,
            "user_message": "How can I avoid checking every pair?",
            "conversation_history": []
        }
    )
    assert hint1_res.status_code == 200
    h1 = hint1_res.json()
    assert h1["hint_level"] == 1
    assert len(h1["hint_text"]) > 0
    assert "guiding_question" in h1

    # 4. Request Level 2 hint with conversation history
    hint2_res = await client.post(
        "/api/v1/coding/problems/two-sum/coach",
        headers=headers,
        json={
            "user_code": "def twoSum(nums, target):\n    lookup = {}\n",
            "language": "python",
            "hint_level": 2,
            "user_message": "What data structure should I use for instantaneous lookups?",
            "conversation_history": [
                {"role": "user", "content": "How can I avoid checking every pair?"},
                {"role": "assistant", "content": h1["hint_text"]}
            ]
        }
    )
    assert hint2_res.status_code == 200
    h2 = hint2_res.json()
    assert h2["hint_level"] == 2
    assert len(h2["hint_text"]) > 0
