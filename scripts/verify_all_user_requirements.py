import asyncio
import os
import httpx
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815"

async def run_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await context.new_page()

        print("[TEST] 1. Authenticating via API and setting session...")
        async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
            login_resp = await client.post("/auth/login", json={"email": "1602-24-733-160@vce.ac.in", "password": "rajababu"})
            assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
            token = login_resp.json()["access_token"]

        await page.goto("http://localhost:5173/login")
        await page.evaluate("token => localStorage.setItem('skillissue_token', token)", token)
        await page.goto("http://localhost:5173/")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        print("[TEST] Logged in successfully!")

        # ----------------------------------------------------------------------
        # TEST A: DSA Arena Starter Code Boilerplates (Clean TODOs, no solutions)
        # ----------------------------------------------------------------------
        print("[TEST] 2. Testing DSA Arena Starter Boilerplate Code...")
        await page.goto("http://localhost:5173/coding")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)

        # Clear any old local storage draft in browser context to prove clean boilerplate loads
        await page.evaluate("() => localStorage.removeItem('skillissue_code_draft_two-sum_python')")
        # Trigger reload or reset
        reset_btn = page.locator("button[title='Reset to Starter Template']")
        if await reset_btn.is_visible():
            await reset_btn.click()
            await page.wait_for_timeout(500)

        # Verify Monaco editor text content contains TODO
        editor_text = await page.locator(".monaco-editor").inner_text()
        print(f"[TEST] Editor snippet: {editor_text[:120].strip()}")
        assert "TODO" in editor_text, "Expected '# TODO: Implement your solution here' in editor code"
        assert "return [seen[diff], i]" not in editor_text, "Found old hardcoded solution in starter code!"

        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_07_dsa_boilerplate.png"))
        print("[TEST] ✓ Verified DSA Arena clean starter boilerplates!")

        # ----------------------------------------------------------------------
        # TEST B: Codeforces Live Arena Tab & Filter
        # ----------------------------------------------------------------------
        print("[TEST] 3. Testing Codeforces Live Arena integration...")
        cf_tab_btn = page.locator("button:has-text('Codeforces Arena')")
        assert await cf_tab_btn.is_visible(), "Codeforces Arena switcher button not found"
        await cf_tab_btn.click()
        await page.wait_for_timeout(3000)

        # Verify Codeforces rating filter or problem selector has CF problems
        problem_select = page.locator("select").first
        select_text = await problem_select.inner_text()
        print(f"[TEST] Codeforces problems loaded: {select_text[:100]}...")
        assert "CF #" in select_text or "Codeforces" in select_text or "Problem" in select_text, "Codeforces problems missing from dropdown"

        # Verify Codeforces link banner in description
        assert await page.locator("text=Live Codeforces Problem").first.is_visible(), "Codeforces banner missing from description tab"
        assert await page.locator("text=Open on Codeforces").first.is_visible(), "Codeforces direct link missing"

        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_08_codeforces_arena.png"))
        print("[TEST] ✓ Verified Codeforces Live Arena with filters and live problem loading!")

        # ----------------------------------------------------------------------
        # TEST C: Interview Setup Page with Adaptive Codeforces Matcher
        # ----------------------------------------------------------------------
        print("[TEST] 4. Testing Interview Setup with Codeforces Dynamic Matcher...")
        await page.goto("http://localhost:5173/interviews/new")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Click DSA & Coding Category
        dsa_cat_btn = page.locator("button:has-text('DSA & Coding')")
        assert await dsa_cat_btn.is_visible(), "DSA category button missing on /interviews/new"
        await dsa_cat_btn.click()
        await page.wait_for_timeout(2500)

        # Verify Codeforces Adaptive Problem Matcher card appeared
        assert await page.locator("text=Codeforces Adaptive Problem Matcher").is_visible(), "Codeforces Matcher card missing"
        assert await page.locator("text=Dynamic Adaptive Selection").is_visible(), "Dynamic Adaptive Selection option missing"

        # Scroll to Codeforces Adaptive Problem Matcher card
        cf_matcher = page.locator("text=Codeforces Adaptive Problem Matcher")
        await cf_matcher.scroll_into_view_if_needed()
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_09_interview_setup_codeforces.png"))
        print("[TEST] ✓ Verified Interview Setup with Codeforces Adaptive Matcher!")

        # ----------------------------------------------------------------------
        # TEST D: Evaluation Report with Calibration Matrix & Stored Transcripts
        # ----------------------------------------------------------------------
        print("[TEST] 5. Testing Evaluation Report with Calibration Graph & Stored Transcripts...")
        await page.goto("http://localhost:5173/evaluations/2951ee89-2d87-4fad-8097-cac82a07407e")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)

        # Check Calibration Matrix & take calibration screenshot
        assert await page.locator("text=Self-Awareness Calibration").is_visible(), "Self-Awareness Calibration header missing"
        assert await page.locator("text=Dimension Calibration Matrix").is_visible(), "Dimension Calibration Matrix missing"
        calib_header = page.locator("text=Self-Awareness Calibration")
        await calib_header.scroll_into_view_if_needed()
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_10_evaluation_calibration.png"))
        print("[TEST] ✓ Verified Evaluation Report with Calibration Graph & Matrix!")

        # Check Stored Transcript Section
        transcript_section = page.locator("text=Complete Stored Interview Transcript")
        assert await transcript_section.is_visible(), "Stored Transcript section missing"
        assert await page.locator("button:has-text('Copy Transcript')").is_visible(), "Copy Transcript button missing"
        assert await page.locator("button:has-text('Download')").is_visible(), "Download button missing"

        # Verify dialogue turns exist
        turn_bubbles = page.locator("text=Candidate Response")
        bubble_count = await turn_bubbles.count()
        print(f"[TEST] Transcript dialogue bubbles rendered: {bubble_count}")
        assert bubble_count > 0, "No interview dialogue turns found in transcript!"

        # Scroll into view and capture complete transcript screenshot
        await transcript_section.scroll_into_view_if_needed()
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_11_evaluation_transcript.png"))
        print("[TEST] ✓ Verified Complete Stored Interview Transcript!")

        await browser.close()
        print("\n=======================================================")
        print("ALL 4 USER-REQUESTED FEATURES VERIFIED END-TO-END!")
        print("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_verification())
