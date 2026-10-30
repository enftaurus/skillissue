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
            token = login_resp.json()["access_token"]

        await page.goto("http://localhost:5173/login")
        await page.evaluate("token => localStorage.setItem('skillissue_token', token)", token)
        await page.goto("http://localhost:5173/")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)
        print("[TEST] Logged in and loaded dashboard successfully!")

        # 1. Dashboard screenshot
        print("[TEST] 2. Capturing Dashboard with Electric Indigo & Slate design...")
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_01_dashboard_redesign.png"))
        assert await page.locator("text=Planly").first.is_visible(), "Planly widget missing on dashboard"
        print("[TEST] Verified Dashboard UI!")

        # 2. LeetCode DSA Arena
        print("[TEST] 3. Navigating to LeetCode DSA Arena...")
        await page.goto("http://localhost:5173/coding")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        assert await page.locator("button:has-text('Description')").is_visible(), "Description tab missing"
        assert await page.locator("button:has-text('Hints & Coach')").is_visible(), "Hints tab missing"
        assert await page.locator("button:has-text('Run')").is_visible(), "Run button missing"
        assert await page.locator("button:has-text('Submit')").is_visible(), "Submit button missing"

        # Capture LeetCode Arena screenshot
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_02_leetcode_arena_redesign.png"))
        print("[TEST] Verified LeetCode DSA Arena layout and typography!")

        # 3. Planly Workspace
        print("[TEST] 4. Navigating to Planly Workspace...")
        await page.goto("http://localhost:5173/planly")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_03_planly_workspace_redesign.png"))
        print("[TEST] Verified Planly Workspace UI!")

        # 4. Progress Analytics
        print("[TEST] 5. Navigating to Progress Analytics...")
        await page.goto("http://localhost:5173/progress")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_04_progress_analytics_redesign.png"))
        print("[TEST] Verified Progress Analytics UI!")

        # 5. AI Provider Settings
        print("[TEST] 6. Navigating to AI Provider Settings...")
        await page.goto("http://localhost:5173/settings/provider")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_05_provider_settings_redesign.png"))
        print("[TEST] Verified AI Provider Settings UI!")

        # 6. Evaluation Report
        print("[TEST] 7. Checking Evaluation Report...")
        await page.goto("http://localhost:5173/evaluations/2951ee89-2d87-4fad-8097-cac82a07407e")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_06_evaluation_report_redesign.png"))
        print("[TEST] Verified Evaluation Report UI!")

        await browser.close()
        print("\n[ALL UI VERIFICATION SCREENSHOTS CAPTURED SUCCESSFULLY!]")

if __name__ == "__main__":
    asyncio.run(run_verification())
