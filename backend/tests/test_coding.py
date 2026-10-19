import uuid
import pytest
import httpx
from backend.app.coding.problems import get_problem

@pytest.mark.asyncio
async def test_coding_sandbox_api(client: httpx.AsyncClient):
    # 1. Register candidate
    email = f"coder_{uuid.uuid4().hex[:8]}@example.com"
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

    # 2. Get problems list
    prob_list = await client.get("/api/v1/coding/problems")
    assert prob_list.status_code == 200
    problems = prob_list.json()
    assert len(problems) >= 2
    assert any(p["id"] == "two-sum" for p in problems)

    # 3. Get single problem
    single_prob = await client.get("/api/v1/coding/problems/two-sum")
    assert single_prob.status_code == 200
    two_sum = single_prob.json()
    assert "python" in two_sum["starter_code"]
    assert "cpp" in two_sum["starter_code"]
    assert "java" in two_sum["starter_code"]

    # 4. Test Python solution execution
    py_code = two_sum["starter_code"]["python"]
    run_py = await client.post(
        "/api/v1/coding/run",
        headers=headers,
        json={"problem_id": "two-sum", "language": "python", "code": py_code}
    )
    assert run_py.status_code == 200
    py_res = run_py.json()
    assert py_res["status"] == "passed"
    assert py_res["total_passed"] == py_res["total_tests"]

    # 5. Test C++ solution execution
    cpp_code = two_sum["starter_code"]["cpp"]
    run_cpp = await client.post(
        "/api/v1/coding/run",
        headers=headers,
        json={"problem_id": "two-sum", "language": "cpp", "code": cpp_code}
    )
    assert run_cpp.status_code == 200
    cpp_res = run_cpp.json()
    assert cpp_res["status"] == "passed"

    # 6. Test Java solution execution
    java_code = two_sum["starter_code"]["java"]
    run_java = await client.post(
        "/api/v1/coding/run",
        headers=headers,
        json={"problem_id": "two-sum", "language": "java", "code": java_code}
    )
    assert run_java.status_code == 200
    java_res = run_java.json()
    assert java_res["status"] == "passed"

    # 7. Submit code solution and record in database
    sub_res = await client.post(
        "/api/v1/coding/submit",
        headers=headers,
        json={"problem_id": "two-sum", "language": "python", "code": py_code}
    )
    assert sub_res.status_code == 201
    sub_data = sub_res.json()
    assert sub_data["status"] == "passed"
    assert sub_data["problem_title"] == two_sum["title"]

    # 8. List user submissions
    list_subs = await client.get("/api/v1/coding/submissions", headers=headers)
    assert list_subs.status_code == 200
    subs = list_subs.json()
    assert len(subs) >= 1
    assert subs[0]["id"] == sub_data["id"]
