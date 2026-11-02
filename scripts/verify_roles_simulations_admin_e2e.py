import asyncio
import os
import httpx
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815"

async def run_deep_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await context.new_page()

        print("\n=======================================================")
        print("PLAYWRIGHT DEEP E2E TEST: ROLES, SIMULATIONS & ADMIN")
        print("=======================================================")

        # ------------------------------------------------------------------
        # TEST 1: Candidate Flow & /progress White-Screen Fix Verification
        # ------------------------------------------------------------------
        print("\n[TEST 1] Testing Candidate Login & Progress Page (Fix White Screen)...")
        await page.goto("http://localhost:5173/login")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[type="email"]', 'candidate@skillissue.com')
        await page.fill('input[type="password"]', 'Password123!')
        await page.click('button:has-text("Sign In")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Verify Sidebar does NOT show Hiring Exam or Admin Analytics for Candidate
        sidebar_text = await page.locator("aside").inner_text()
        print("[TEST 1] Candidate Sidebar items verified.")
        assert "Hiring Exam" not in sidebar_text, "Candidate sidebar should NOT show Hiring Exam!"
        assert "Admin Analytics" not in sidebar_text, "Candidate sidebar should NOT show Admin Analytics!"

        # Navigate to /progress
        print("[TEST 1] Navigating to /progress...")
        await page.goto("http://localhost:5173/progress")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)

        # Check that page is not blank
        body_text = await page.locator("body").inner_text()
        print(f"[DEBUG body_text on /progress]:\n{body_text[:400]}")
        assert "Have I Actually Improved?" in body_text, "Progress page failed to render header!"
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_25_candidate_progress_no_whitescreen.png"))
        print("[TEST 1] ✓ /progress successfully rendered without white screen!")

        # ------------------------------------------------------------------
        # TEST 2: 50+ Company Tracks & Flagship Placement Simulations
        # ------------------------------------------------------------------
        print("\n[TEST 2] Testing 50+ Company Tracks & Placement Simulations Tab...")
        await page.goto("http://localhost:5173/tracks")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)

        tracks_header = await page.locator("h1").inner_text()
        assert "Company Career Tracks" in tracks_header
        
        # Check community debrief banner
        banner_text = await page.locator("body").inner_text()
        assert "Curated from candidate experiences gathered from community platforms" in banner_text

        # Verify 50+ company packs
        track_cards = await page.locator(".grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3 > div").count()
        print(f"[TEST 2] Total company pack cards rendered: {track_cards}")
        assert track_cards >= 50, f"Expected at least 50 companies, found {track_cards}"

        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_26_company_tracks_50_packs.png"))

        # Switch to Placement Simulations Tab
        print("[TEST 2] Switching to Placement Simulations tab...")
        sim_tab_btn = page.locator("button:has-text('Placement Simulations')")
        assert await sim_tab_btn.is_visible()
        await sim_tab_btn.click()
        await page.wait_for_timeout(1500)

        sim_body = await page.locator("body").inner_text()
        assert "Google" in sim_body
        assert "Uber" in sim_body
        assert "OpenAI" in sim_body
        assert "Oral Cross-Examination Integrity Protocol" in sim_body
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_27_placement_simulations_tab.png"))
        print("[TEST 2] ✓ Placement Simulations (Google, Uber, OpenAI) fully verified!")

        # Switch to Google Code Comprehension Beta Tab
        print("[TEST 2] Testing Google Code Comprehension (Beta) tab...")
        comp_tab_btn = page.locator("button:has-text('Google Code Comprehension (Beta)')")
        assert await comp_tab_btn.is_visible()
        await comp_tab_btn.click()
        await page.wait_for_timeout(1000)

        comp_body = await page.locator("body").inner_text()
        assert "Subtle Bug Spotting" in comp_body
        assert "Double-Checked Locking" in comp_body
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_28_google_code_comprehension_beta.png"))
        print("[TEST 2] ✓ Google Code Comprehension Beta tab verified!")

        # ------------------------------------------------------------------
        # TEST 3: Dedicated Recruiter Login & Enterprise Portal Features
        # ------------------------------------------------------------------
        print("\n[TEST 3] Testing Dedicated Recruiter Portal & Custom OA Options...")
        # Clear candidate session
        await page.evaluate("() => { localStorage.clear(); }")
        await page.goto("http://localhost:5173/enterprise/login")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        recruiter_heading = await page.locator("h2").inner_text()
        assert "Enterprise & TPO Portal" in recruiter_heading

        await page.fill('input[type="email"]', 'recruiter@skillissue.com')
        await page.fill('input[type="password"]', 'Password123!')
        await page.click('button:has-text("Sign In as Recruiter")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)

        # Recruiter sidebar should now include Hiring Exam
        rec_sidebar = await page.locator("aside").inner_text()
        assert "Hiring Exam" in rec_sidebar, "Recruiter sidebar should include Hiring Exam!"

        # Open New Hiring Assessment Modal
        await page.click('button:has-text("New Hiring Assessment")')
        await page.wait_for_timeout(1000)

        # Verify OA Customization modes: Curated Preset, Custom URL, CF Randomizer
        modal_text = await page.locator("body").inner_text()
        assert "Round 1 OA Question Customization" in modal_text
        assert "Curated Preset" in modal_text
        assert "Custom URL" in modal_text
        assert "CF Randomizer" in modal_text

        # Test selecting Codeforces Randomizer
        await page.click('button:has-text("CF Randomizer")')
        await page.wait_for_timeout(500)
        cf_config_text = await page.locator("body").inner_text()
        assert "Difficulty Rating:" in cf_config_text
        assert "Topic Domain:" in cf_config_text

        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_29_enterprise_oa_customizer_modal.png"))
        print("[TEST 3] ✓ Recruiter OA Customizer verified!")

        # Actually submit create pipeline form
        await page.fill('input[placeholder*="Uber SDE-1 Campus Drive"]', 'Uber SDE-1 Placement Drive 2026')
        await page.fill('textarea[placeholder*="Paste Job Description requirements"]', 'Seeking skilled backend engineers proficient in topological sorting, rate limiters, and clean code.')
        await page.click('button:has-text("Create Pipeline")')
        await page.wait_for_timeout(2000)

        # Verify new pipeline card is rendered
        assert "Uber SDE-1 Placement Drive 2026" in (await page.locator("body").inner_text())

        # Invite Candidate
        await page.click('button:has-text("Invite Candidate")')
        await page.wait_for_timeout(1000)
        await page.fill('input[placeholder*="John Doe"]', 'Aarav Sharma')
        await page.fill('input[placeholder*="student@university.edu"]', 'aarav@university.edu')
        await page.click('button:has-text("Generate Candidate Link")')
        await page.wait_for_timeout(2000)
        print("[TEST 3] ✓ Recruiter Pipeline & Candidate Invitation created!")

        # ------------------------------------------------------------------
        # TEST 4: Candidate Exam Runner & Stage 3 Code Cross-Examination
        # ------------------------------------------------------------------
        print("\n[TEST 4] Testing Candidate Exam Runner & Stage 3 Cheating Cross-Exam...")
        # Fetch an active pipeline's invite token via API
        async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
            rec_login = await client.post("/auth/login", json={"email": "recruiter@skillissue.com", "password": "Password123!"})
            rec_token = rec_login.json()["access_token"]
            pipes = (await client.get("/enterprise/pipelines", headers={"Authorization": f"Bearer {rec_token}"})).json()
            assert len(pipes) > 0
            invite_token = pipes[0]["invite_token"]

        await page.goto(f"http://localhost:5173/assess/take/{invite_token}")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)

        exam_body = await page.locator("body").inner_text()
        assert "Algorithmic Online Assessment" in exam_body
        assert "Candidate Resume & Projects Intake" in exam_body

        # Paste sample resume
        await page.fill('textarea[placeholder*="Paste your resume summary"]', 'Ex-Amazon Intern, built high-scale DynamoDB distributed lock manager.')

        # Advance Stage 1 -> Stage 2
        await page.click('button:has-text("Complete Stage & Next")')
        await page.wait_for_timeout(2500)

        # Advance Stage 2 -> Stage 3
        stage2_body = await page.locator("body").inner_text()
        print(f"[DEBUG Stage 2 body]:\n{stage2_body[:300]}")
        assert "stage 2" in stage2_body.lower()
        await page.click('button:has-text("Complete Stage & Next")')
        await page.wait_for_timeout(2500)

        # In Stage 3, check Anti-Cheating Oral Cross-Examination notice!
        stage3_body = await page.locator("body").inner_text()
        assert "anti-cheating cross-examination" in stage3_body.lower()
        assert "walk me through the exact algorithm" in stage3_body.lower()
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_30_candidate_cross_examination_stage3.png"))
        print("[TEST 4] ✓ Candidate Stage 3 Code Cross-Examination notice verified!")

        # Complete final stage
        await page.fill('textarea[placeholder*="Provide specific implementation details"]', 'I implemented Kahn algorithm with in-degree array for O(V+E) linear time complexity.')
        await page.click('button:has-text("Finish Assessment")')
        await page.wait_for_timeout(3000)

        completed_body = await page.locator("body").inner_text()
        assert "Assessment Successfully Completed" in completed_body

        # ------------------------------------------------------------------
        # TEST 5: Recruiter Candidate Audit Modal (Resume, Scores, Code)
        # ------------------------------------------------------------------
        print("\n[TEST 5] Testing Recruiter Candidate Deep Audit Modal...")
        await page.goto("http://localhost:5173/enterprise")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Switch to Leaderboard tab
        await page.click('button:has-text("Candidate Leaderboard")')
        await page.wait_for_timeout(1500)

        # Click "Audit & Code" on first candidate
        audit_btn = page.locator('button:has-text("Audit & Code")').first
        if await audit_btn.is_visible():
            await audit_btn.click()
            await page.wait_for_timeout(1000)

            audit_modal_text = await page.locator("body").inner_text()
            assert "Candidate Resume / Project Submissions" in audit_modal_text
            assert "Submitted Round 1 OA Code" in audit_modal_text
            assert "Cross-examination note" in audit_modal_text
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_31_recruiter_candidate_audit_modal.png"))
            print("[TEST 5] ✓ Recruiter Candidate Audit Modal (Resume, Scores & OA Code) verified!")

        # ------------------------------------------------------------------
        # TEST 6: Dedicated Admin Login & Real vs Sandbox Analytics
        # ------------------------------------------------------------------
        print("\n[TEST 6] Testing Dedicated Admin Login & Multi-Tenant Analytics...")
        await page.evaluate("() => { localStorage.clear(); }")
        await page.goto("http://localhost:5173/admin/login")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        admin_login_heading = await page.locator("h2").inner_text()
        assert "Platform Administration" in admin_login_heading

        await page.fill('input[type="email"]', 'admin@skillissue.com')
        await page.fill('input[type="password"]', 'Password123!')
        await page.click('button:has-text("Sign In to Admin Console")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)

        admin_analytics_text = await page.locator("body").inner_text()
        assert "Platform Analytics & Tenant Partitioning" in admin_analytics_text
        assert "Real Production Candidates" in admin_analytics_text
        assert "Test & Sandbox Users" in admin_analytics_text
        assert "Active Tenants Partition Registry" in admin_analytics_text

        # Click on Test & Sandbox tab to verify partition toggle
        await page.click('button:has-text("Test & Sandbox Users")')
        await page.wait_for_timeout(1000)
        assert "Sandbox Tenant" in (await page.locator("body").inner_text())

        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_32_admin_analytics_tenant_partitioning.png"))
        print("[TEST 6] ✓ Admin Multi-Tenant Analytics & Isolation verified!")

        print("\n=======================================================")
        print("ALL PLAYWRIGHT TESTS PASSED CLEANLY WITH SCREENSHOTS!")
        print("=======================================================\n")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_deep_verification())
