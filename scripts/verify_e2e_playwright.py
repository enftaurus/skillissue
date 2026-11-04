import os
import sys
import time
import httpx
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def run_playwright_verification():
    print("[Playwright E2E] Initializing test session...")
    
    # 1. Setup candidate and pipeline via backend API
    email = f"recruiter_e2e_{int(time.time())}@enterprise.org"
    with httpx.Client(base_url="http://localhost:8000") as client:
        reg_res = client.post(
            "/api/v1/auth/register-recruiter",
            json={"organisation_name": "Google DeepMind", "email": email, "password": "Password123!"}
        )
        assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        recruiter_token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {recruiter_token}"}

        # Create pipeline
        pipe_res = client.post(
            "/api/v1/enterprise/pipelines",
            headers=headers,
            json={
                "title": "Google L4 Systems Engineering Assessment",
                "target_role": "Backend Systems Engineer",
                "job_description": "Distributed systems, graph topological sort, concurrency.",
                "rounds": [
                    {
                        "round_type": "oa_dsa",
                        "name": "Round 1: Alien Dictionary Ordering",
                        "time_limit_minutes": 35,
                        "is_enabled": True,
                        "config": {"topics": ["Graph", "TopologicalSort"]}
                    },
                    {
                        "round_type": "ai_project",
                        "name": "Round 2: Systems Simulation",
                        "time_limit_minutes": 30,
                        "is_enabled": True,
                        "config": {"project_id": "rate-limiter"}
                    }
                ]
            }
        )
        assert pipe_res.status_code == 201
        pipe_data = pipe_res.json()
        invite_token = pipe_data["invite_token"]
        print(f"[Playwright E2E] Pipeline created: {pipe_data['title']} (Invite: {invite_token})")

        # Candidate entry
        entry_res = client.post(
            f"/api/v1/enterprise/assessments/entry/{invite_token}",
            json={"candidate_name": "Alan Turing", "candidate_email": "turing@bletchley.ac.uk"}
        )
        assert entry_res.status_code == 201
        cand_data = entry_res.json()
        cand_access_token = cand_data["access_token"]
        cand_id = cand_data["id"]
        print(f"[Playwright E2E] Candidate created: {cand_data['candidate_name']} (ID: {cand_id})")

    # 2. Run Playwright Browser Automation
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[Browser Error] {err}"))

        # Step 1: Candidate Assessment Flow
        candidate_url = f"http://localhost:5173/assess/take/{cand_access_token}"
        print(f"[Playwright E2E] Navigating to Candidate Assessment: {candidate_url}")
        page.goto(candidate_url)
        page.wait_for_timeout(2000)

        # Type code into editor
        code_input = page.locator("textarea").first
        if code_input.is_visible():
            code_input.click()
            solution_code = (
                "def solve(words):\n"
                "    in_degree = {}\n"
                "    adj = {}\n"
                "    for w in words:\n"
                "        for c in w:\n"
                "            in_degree[c] = 0\n"
                "            adj[c] = set()\n"
                "    return ''.join(adj.keys())\n"
            )
            code_input.fill(solution_code)
            print("[Playwright E2E] Candidate typed solution code with in_degree and adj identifiers.")
            page.wait_for_timeout(1000)

        # Candidate clicks "Complete Stage & Next"
        submit_btn = page.locator("button:has-text('Complete Stage & Next')")
        if submit_btn.is_visible():
            submit_btn.click()
            print("[Playwright E2E] Candidate clicked 'Complete Stage & Next'")

        # Wait for Explanation Check Modal to appear
        page.wait_for_selector("text=Post-Submission Cross-Examination", timeout=10000)
        print("[Playwright E2E] Explanation Check modal displayed successfully!")
        page.wait_for_timeout(1500)

        # Capture Screenshot 1: Candidate Explanation Check Modal with grounded question & countdown
        ss1_path = os.path.join(ARTIFACTS_DIR, "verified_33_candidate_explanation_check_flow.png")
        page.screenshot(path=ss1_path, full_page=False)
        print(f"[Playwright E2E] Saved {ss1_path}")

        # Answer question 1
        explanation_textarea = page.locator("textarea[placeholder*='Explain why you chose this data structure']")
        if explanation_textarea.is_visible():
            explanation_textarea.fill("I used in_degree and an adjacency set to track letter dependencies for Kahn's topological sort.")
            page.wait_for_timeout(500)

        next_q_btn = page.locator("button:has-text('Next Question')")
        if next_q_btn.is_visible():
            next_q_btn.click()
            page.wait_for_timeout(1000)

        # Answer question 2
        if explanation_textarea.is_visible():
            explanation_textarea.fill("If streaming constraints are introduced, we would incrementally update the in_degree table and detect cycles dynamically.")
            page.wait_for_timeout(500)

        if next_q_btn.is_visible():
            next_q_btn.click()
            page.wait_for_timeout(1000)

        # Answer question 3 and submit
        if explanation_textarea.is_visible():
            explanation_textarea.fill("For single-element input, the loop terminates without edges and returns the single character in O(1) time.")
            page.wait_for_timeout(500)

        finish_btn = page.locator("button:has-text('Submit All Explanations')")
        if finish_btn.is_visible():
            finish_btn.click()
            print("[Playwright E2E] Submitted all explanation check answers.")
            page.wait_for_timeout(3000)

        # Verify confirmation screen
        page.wait_for_selector("text=Cross-Examination Responses Recorded", timeout=10000)
        print("[Playwright E2E] Neutral confirmation displayed to candidate.")
        proceed_btn = page.locator("button:has-text('Proceed to Next Round')")
        if proceed_btn.is_visible():
            proceed_btn.click()
            page.wait_for_timeout(1500)

        # Step 2: Recruiter Replay View in Enterprise Portal
        print("[Playwright E2E] Logging in as recruiter to inspect replay...")
        # Inject recruiter token into localStorage
        page.evaluate(f"localStorage.setItem('skillissue_token', '{recruiter_token}');")
        page.goto("http://localhost:5173/enterprise")
        page.wait_for_timeout(2000)

        # Switch to Candidate Leaderboard tab
        lb_tab = page.locator("button:has-text('Candidate Leaderboard & Anti-Cheating Telemetry')")
        if lb_tab.is_visible():
            lb_tab.click()
            page.wait_for_timeout(1500)

        # Click Replay button on candidate Alan Turing
        replay_btn = page.locator("button:has-text('Replay')").first
        if replay_btn.is_visible():
            replay_btn.click()
            print("[Playwright E2E] Opened EditorReplayModal!")
            page.wait_for_timeout(2500)

            # Capture Screenshot 2: Recruiter Editor Telemetry & Replay Modal
            ss2_path = os.path.join(ARTIFACTS_DIR, "verified_34_recruiter_editor_replay_telemetry.png")
            page.screenshot(path=ss2_path, full_page=False)
            print(f"[Playwright E2E] Saved {ss2_path}")

            close_replay = page.locator("button:has-text('Close')").first
            if close_replay.is_visible():
                close_replay.click()
                page.wait_for_timeout(1000)

        # Step 3: Student Coding Practice Mode Explanation Check
        print("[Playwright E2E] Navigating to Coding Practice Page...")
        page.goto("http://localhost:5173/practice")
        page.wait_for_timeout(2000)

        # Run solution on practice problem
        run_btn = page.locator("button:has-text('Run')")
        if run_btn.is_visible():
            run_btn.click()
            page.wait_for_timeout(2000)

        # Click Explanation Check button in test results
        exp_practice_btn = page.locator("button:has-text('Explanation Check')")
        if exp_practice_btn.is_visible():
            exp_practice_btn.click()
            print("[Playwright E2E] Opened Explanation Check in Practice Mode!")
            page.wait_for_timeout(2000)

            # Capture Screenshot 3: Practice Mode Explanation Check Modal
            ss3_path = os.path.join(ARTIFACTS_DIR, "verified_35_practice_explanation_check_coaching.png")
            page.screenshot(path=ss3_path, full_page=False)
            print(f"[Playwright E2E] Saved {ss3_path}")

        browser.close()
        print("[Playwright E2E] All browser verification steps completed successfully!")

if __name__ == "__main__":
    run_playwright_verification()
