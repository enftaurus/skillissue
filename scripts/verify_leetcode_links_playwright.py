import asyncio
from playwright.async_api import async_playwright
import httpx

async def main():
    print("[Playwright Test] Verifying Company Track LeetCode Links & Progressive Unlock...")
    
    # Register/login user via API
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Add console logger
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))

        # Log in via UI
        print("[Playwright Test] Logging in as candidate@skillissue.com...")
        await page.goto("http://localhost:5173/login")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[type="email"]', 'candidate@skillissue.com')
        await page.fill('input[type="password"]', 'Password123!')
        await page.click('button:has-text("Sign In")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Add console logger
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))

        # Navigate to Uber Company Track Detail
        print("[Playwright Test] Navigating to http://localhost:5173/tracks/uber...")
        await page.goto("http://localhost:5173/tracks/uber")
        await page.wait_for_timeout(2000)
        print(f"[Playwright Test] Current URL: {page.url}")
        await page.wait_for_selector("text=Uber Career Track", timeout=10000)
        await page.wait_for_selector("text=Solve on LeetCode", timeout=10000)
        
        # Verify LeetCode links exist on page
        leetcode_links = await page.locator("a[href*='leetcode.com/problems']").count()
        print(f"[Playwright Test] Found {leetcode_links} LeetCode links on the page!")
        assert leetcode_links >= 3, f"Expected at least 3 LeetCode links, got {leetcode_links}"

        # Verify initial unlock state (3 problems available)
        await page.wait_for_selector("text=3 of 5 Problems Available")
        print("[Playwright Test] Initial state verified: 3 of 5 Problems Available")

        # Click "Mark Solved" on the first problem
        mark_solved_btn = page.locator("button:has-text('Mark Solved')").first
        await mark_solved_btn.click()

        # Wait for Toast or state update
        await page.wait_for_selector("text=4 of 5 Problems Available", timeout=10000)
        print("[Playwright Test] Successfully unlocked 4th question upon marking problem 1 as solved!")

        # Take screenshot
        screenshot_path = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815/verified_35_company_track_leetcode_links.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"[Playwright Test] Saved screenshot to {screenshot_path}")

        await browser.close()
    print("[Playwright Test] Verification successfully completed!")

if __name__ == "__main__":
    asyncio.run(main())
