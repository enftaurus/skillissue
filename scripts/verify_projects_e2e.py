import asyncio
import os
import sys
import time
import httpx
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815"
BASE_URL = "http://localhost:5173"
API_URL = "http://localhost:8000/api/v1"
EMAIL = "1602-24-733-160@vce.ac.in"
PASSWORD = "rajababu"

async def main():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    print("Starting Playwright E2E verification for AI-Assisted Projects...")

    # 1. Authenticate via API
    async with httpx.AsyncClient(base_url=API_URL) as client:
        res = await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert res.status_code == 200, f"Login failed: {res.text}"
        token = res.json()["access_token"]
        print("Obtained authentication token.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Set token in browser
        await page.goto(f"{BASE_URL}/login")
        await page.evaluate("token => localStorage.setItem('skillissue_token', token)", token)
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        print("Logged in successfully to Dashboard.")

        # 2. Check sidebar contains 'AI Projects'
        projects_link = page.locator("a[href='/projects']")
        await projects_link.wait_for(state="visible", timeout=10000)
        print("Found AI Projects link in sidebar.")

        # Click AI Projects link
        await projects_link.click()
        await page.wait_for_url(f"{BASE_URL}/projects", timeout=10000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)

        # 3. Verify Project Catalog Page
        assert await page.locator("text=AI-Assisted Coding Projects").is_visible(), "Catalog title missing!"
        assert await page.locator("text=Design a Distributed Rate Limiter Middleware").is_visible(), "Project 1 missing!"
        assert await page.locator("text=Async Task Queue with Priority & Dead-Letter Retries").is_visible(), "Project 2 missing!"
        print("Catalog page rendered both demo projects successfully.")

        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_12_projects_catalog.png"))
        print("Captured verified_12_projects_catalog.png")

        # 4. Launch Project 1: Distributed Rate Limiter
        print("Launching Distributed Rate Limiter workspace...")
        await page.locator("button:has-text('Launch Workspace')").first.click()
        await page.wait_for_url("**/projects/distributed-rate-limiter", timeout=10000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)

        # Verify 25-minute countdown timer
        timer_el = page.locator("header div:has-text(':')").first
        timer_text = await timer_el.text_content()
        print(f"Countdown timer visible: {timer_text.strip()}")
        assert "2" in timer_text and ":" in timer_text, f"Unexpected timer value: {timer_text}"

        # Verify File Explorer
        assert await page.locator("button:has-text('src/limiter.py')").is_visible(), "src/limiter.py missing in file tree!"
        assert await page.locator("button:has-text('tests/test_rate_limiter.py')").is_visible(), "tests missing in tree!"
        print("Verified multi-file virtual tree.")

        # 5. Test Read-Only Copilot with amateurish prompts
        print("Testing Read-Only Copilot with amateur prompt...")
        copilot_textarea = page.locator("textarea[placeholder*='Ask about architecture']")
        await copilot_textarea.fill("it doesnt work fix it")
        await page.click("button:has-text('Send')")

        # Wait for Copilot response
        await page.wait_for_timeout(4000)
        copilot_text_1 = await page.locator("div.prose").last.text_content()
        print(f"Copilot Response 1 snippet: {copilot_text_1[:150]}...")
        assert "read-only" in copilot_text_1.lower() or "cannot" in copilot_text_1.lower() or "src/limiter.py" in copilot_text_1.lower(), "Guardrail failed!"

        # Send second amateur prompt
        await page.wait_for_timeout(1000)
        await copilot_textarea.fill("give me the code")
        await page.click("button:has-text('Send')")
        await page.wait_for_timeout(4000)

        # Send third technical question
        await copilot_textarea.fill("In src/limiter.py, does zremrangebyscore evict timestamps before zcard is evaluated?")
        await page.click("button:has-text('Send')")
        await page.wait_for_timeout(4000)

        # 6. Run CI/CD Tests
        print("Clicking Run CI/CD Tests button...")
        await page.click("button:has-text('Run CI/CD Tests')")
        await page.wait_for_selector("div:has-text('Tests Passed')", timeout=20000)
        console_summary = await page.locator("div:has-text('Tests Passed')").first.text_content()
        print(f"CI/CD Test Runner executed: {console_summary}")

        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_13_project_workspace_copilot.png"))
        print("Captured verified_13_project_workspace_copilot.png")

        # 7. Submit Project & Check Prompt Analysis Modal
        print("Submitting project for prompt analysis...")
        await page.click("button:has-text('Submit & Analyze Prompts')")

        # Wait for Prompt Quality Modal
        await page.wait_for_selector("h2:has-text('Prompt Quality Report')", timeout=15000)
        assert await page.locator("text=Prompt Score").is_visible(), "Prompt score banner missing!"
        assert await page.locator("text=Amateurish Prompt Flagged").first.is_visible(), "Amateur prompt flag missing!"
        assert await page.locator("text=How a Staff / Senior Engineer would ask this").first.is_visible(), "Senior rewrite missing!"

        print("Prompt Quality Report successfully detected amateurish prompts and provided senior rewrites.")

        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_14_project_prompt_analysis_modal.png"))
        print("Captured verified_14_project_prompt_analysis_modal.png")

        # Close modal
        await page.click("button:has-text('Close Report')")
        await page.wait_for_timeout(1000)

        # 8. Test Project 2: Async Job Queue
        print("Navigating to Project 2: Async Job Queue...")
        await page.goto(f"{BASE_URL}/projects/async-job-queue")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_selector("text=Async Task Queue with Priority", timeout=10000)
        await page.wait_for_timeout(1500)

        # Run CI/CD tests on Project 2
        await page.click("button:has-text('Run CI/CD Tests')")
        await page.wait_for_selector("div:has-text('Tests Passed')", timeout=20000)
        p2_summary = await page.locator("div:has-text('Tests Passed')").first.text_content()
        print(f"Project 2 CI/CD Result: {p2_summary}")

        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_15_project_async_queue.png"))
        print("Captured verified_15_project_async_queue.png")

        await browser.close()
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
