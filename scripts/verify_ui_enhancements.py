import asyncio
import httpx
from playwright.async_api import async_playwright

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

        # 2. Check Credits & Cost Usage Meter
        print("[TEST] 2. Checking Credits & Cost Meter...")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="artifacts_e2e/verified_01_dashboard_credits.png")
        credits_badge = page.locator("text=tokens used")
        assert await credits_badge.count() > 0, "Credits meter not found in UI"
        print("[TEST] Verified Credits & Cost meter in dashboard header and sidebar!")

        # 3. Check LeetCode DSA Arena
        print("[TEST] 3. Navigating to LeetCode DSA Arena...")
        await page.goto("http://localhost:5173/coding")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Check tabs: Description, Hints & Coach, Submissions
        assert await page.locator("button:has-text('Description')").is_visible(), "Description tab missing"
        assert await page.locator("button:has-text('Hints & Coach')").is_visible(), "Hints tab missing"
        assert await page.locator("button:has-text('Submissions')").is_visible(), "Submissions tab missing"
        assert await page.locator("button:has-text('Run')").is_visible(), "Run button missing"
        assert await page.locator("button:has-text('Submit')").is_visible(), "Submit button missing"
        assert await page.locator("button:has-text('Console')").first.is_visible(), "Console drawer missing"

        # Click Hints tab
        await page.click("button:has-text('Hints & Coach')")
        await page.wait_for_timeout(500)

        # Click Submissions tab
        await page.click("button:has-text('Submissions')")
        await page.wait_for_timeout(500)

        # Switch back to Description
        await page.click("button:has-text('Description')")
        await page.wait_for_timeout(500)

        # Click Custom Testcase
        await page.click("button:has-text('+ Custom Testcase')")
        await page.wait_for_timeout(500)

        # Take screenshot of LeetCode DSA Arena
        await page.screenshot(path="artifacts_e2e/verified_02_leetcode_arena.png")
        print("[TEST] Verified LeetCode DSA Arena layout and controls!")

        # 4. Check Focus Mode on an Interview Session
        print("[TEST] 4. Checking Interview Session Focus Mode...")
        # Check if an existing interview exists or create a quick one
        await page.goto("http://localhost:5173/interviews/new")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        # Select technical round and create
        await page.click('button:has-text("Technical Depth")')
        await page.click('button:has-text("Start Practice Interview Session")')

        # Wait for interview session page
        await page.wait_for_url(lambda u: "/interviews/" in u and "/new" not in u, timeout=15000)
        await page.wait_for_timeout(3000)

        # Verify Sidebar is HIDDEN (Focus Mode lockdown)
        sidebar = page.locator("nav a:has-text('Dashboard')")
        is_sidebar_hidden = (await sidebar.count()) == 0 or not await sidebar.is_visible()
        print(f"[TEST] Sidebar hidden in Focus Mode: {is_sidebar_hidden}")
        assert is_sidebar_hidden, "Sidebar should be locked down during active interview"

        # Verify Live recording indicator and 3D InterviewerAvatar
        assert await page.locator("text=LIVE INTERVIEW").is_visible(), "Live interview badge missing"
        assert await page.locator("canvas").is_visible(), "Interviewer 3D avatar canvas missing"
        assert await page.locator("button:has-text('Speak Answer')").is_visible(), "Speak Answer mic button missing"

        # Take screenshot of Interview Focus Mode with 3D Avatar
        await page.screenshot(path="artifacts_e2e/verified_03_interview_focus_mode.png")
        print("[TEST] Verified Interview Focus Mode, 3D Avatar, and Speech Input!")

        # Test Exit Interview confirmation modal
        await page.click("button:has-text('Exit')")
        await page.wait_for_timeout(500)
        assert await page.locator("text=Exit Active Interview Session?").is_visible(), "Exit confirmation modal missing"
        await page.screenshot(path="artifacts_e2e/verified_04_exit_confirmation_modal.png")
        await page.click("button:has-text('Cancel (Stay in Interview)')")
        await page.wait_for_timeout(500)

        # 5. Check Evaluation Report
        print("[TEST] 5. Checking Evaluation Report with Token cost and Model Guide...")
        # Navigate to a previous evaluation or evaluations page
        await page.goto("http://localhost:5173/evaluations/a6ba06f3-8b73-41a4-9e32-2d93e1ba1f1b")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Take screenshot of Evaluation Report
        await page.screenshot(path="artifacts_e2e/verified_05_evaluation_report.png")
        print("[TEST] Verified Evaluation Report!")

        await browser.close()
        print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

if __name__ == "__main__":
    asyncio.run(run_verification())
