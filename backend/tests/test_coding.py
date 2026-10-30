import uuid
import pytest
import httpx
from backend.app.coding.problems import get_problem

@pytest.mark.asyncio
async def test_coding_sandbox_api(client: httpx.AsyncClient):
    # 1. Unauthenticated request to /problems rejected
    unauth_res = await client.get("/api/v1/coding/problems")
    assert unauth_res.status_code == 401

    # 2. Limits endpoint is publicly accessible
    limits_res = await client.get("/api/v1/coding/limits")
    assert limits_res.status_code == 200
    limits_data = limits_res.json()
    assert limits_data["memory_limit_mb"] == 256
    assert limits_data["time_limit_seconds"] == 3.0
    assert "python" in limits_data["supported_languages"]

    # 3. Register candidate
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

    # 4. Authenticated problems list (15 problems, public schema only)
    prob_list = await client.get("/api/v1/coding/problems", headers=headers)
    assert prob_list.status_code == 200
    problems = prob_list.json()
    assert len(problems) >= 15
    assert any(p["id"] == "two-sum" for p in problems)
    # Ensure test_cases is NOT in the public schema
    assert "test_cases" not in problems[0]

    # 5. Get single problem
    single_prob = await client.get("/api/v1/coding/problems/two-sum", headers=headers)
    assert single_prob.status_code == 200
    two_sum = single_prob.json()
    assert "python" in two_sum["starter_code"]
    assert "cpp" in two_sum["starter_code"]
    assert "java" in two_sum["starter_code"]
    assert "# TODO: Implement your solution here" in two_sum["starter_code"]["python"]
    assert "test_cases" not in two_sum

    # 6. Test Python solution execution
    py_code = """import sys

def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return seen[diff], i
        seen[num] = i
    return 0, 0

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        nums = [int(x) for x in lines[1:n+1]]
        target = int(lines[n+1])
        i, j = two_sum(nums, target)
        print(f"{min(i, j)} {max(i, j)}")
"""
    run_py = await client.post(
        "/api/v1/coding/run",
        headers=headers,
        json={"problem_id": "two-sum", "language": "python", "code": py_code}
    )
    assert run_py.status_code == 200
    py_res = run_py.json()
    assert py_res["status"] == "passed"
    assert py_res["total_passed"] == py_res["total_tests"]

    # 7. Test C++ solution execution
    cpp_code = """#include <iostream>
#include <vector>
#include <unordered_map>
#include <algorithm>

using namespace std;

int main() {
    int n;
    if (!(cin >> n)) return 0;
    vector<int> nums(n);
    for (int i = 0; i < n; ++i) cin >> nums[i];
    int target;
    cin >> target;

    unordered_map<int, int> seen;
    for (int i = 0; i < n; ++i) {
        int comp = target - nums[i];
        if (seen.find(comp) != seen.end()) {
            cout << min(seen[comp], i) << " " << max(seen[comp], i) << endl;
            return 0;
        }
        seen[nums[i]] = i;
    }
    return 0;
}
"""
    run_cpp = await client.post(
        "/api/v1/coding/run",
        headers=headers,
        json={"problem_id": "two-sum", "language": "cpp", "code": cpp_code}
    )
    assert run_cpp.status_code == 200
    cpp_res = run_cpp.json()
    assert cpp_res["status"] == "passed"

    # 8. Test Java solution execution
    java_code = """import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        int[] nums = new int[n];
        for (int i = 0; i < n; i++) nums[i] = sc.nextInt();
        int target = sc.nextInt();

        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < n; i++) {
            int comp = target - nums[i];
            if (seen.containsKey(comp)) {
                System.out.println(Math.min(seen.get(comp), i) + " " + Math.max(seen.get(comp), i));
                return;
            }
            seen.put(nums[i], i);
        }
    }
}
"""
    run_java = await client.post(
        "/api/v1/coding/run",
        headers=headers,
        json={"problem_id": "two-sum", "language": "java", "code": java_code}
    )
    assert run_java.status_code == 200
    java_res = run_java.json()
    assert java_res["status"] == "passed"

    # 9. Submit code solution and record in database with masked hidden tests
    sub_res = await client.post(
        "/api/v1/coding/submit",
        headers=headers,
        json={"problem_id": "two-sum", "language": "python", "code": py_code}
    )
    assert sub_res.status_code == 201
    sub_data = sub_res.json()
    assert sub_data["status"] == "passed"
    assert sub_data["problem_title"] == two_sum["title"]
    assert sub_data["tests_passed"] > 0
    assert sub_data["tests_total"] > 0
    # Verify hidden test results have masked inputs and outputs
    for tc in sub_data["test_results"]:
        if tc["is_hidden"]:
            assert tc["stdin"] is None
            assert tc["expected_stdout"] is None

    # 10. List user submissions
    list_subs = await client.get("/api/v1/coding/submissions", headers=headers)
    assert list_subs.status_code == 200
    subs = list_subs.json()
    assert len(subs) >= 1
    assert subs[0]["id"] == sub_data["id"]

@pytest.mark.asyncio
async def test_coding_submission_idor_protection(client: httpx.AsyncClient):
    """Verify submitting code with an interview_id belonging to another user fails with 404."""
    # User A
    uA = await client.post("/api/v1/auth/register", json={"email": f"a_{uuid.uuid4().hex[:6]}@test.com", "password": "Password123!"})
    tA = (await client.post("/api/v1/auth/login", json={"email": uA.json()["email"], "password": "Password123!"})).json()["access_token"]

    # User B
    uB = await client.post("/api/v1/auth/register", json={"email": f"b_{uuid.uuid4().hex[:6]}@test.com", "password": "Password123!"})
    tB = (await client.post("/api/v1/auth/login", json={"email": uB.json()["email"], "password": "Password123!"})).json()["access_token"]

    # User A creates interview
    inv = await client.post(
        "/api/v1/interviews/domain",
        headers={"Authorization": f"Bearer {tA}"},
        json={"category": "technical", "domain_skills": ["python"]}
    )
    inv_id = inv.json()["id"]

    # User B attempts to submit coding solution linked to User A's interview
    fake_sub = await client.post(
        f"/api/v1/coding/submit?interview_id={inv_id}",
        headers={"Authorization": f"Bearer {tB}"},
        json={"problem_id": "two-sum", "language": "python", "code": "print('1 2')"}
    )
    assert fake_sub.status_code == 404
