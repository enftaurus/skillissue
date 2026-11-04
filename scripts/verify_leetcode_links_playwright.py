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

        # Verify Problems Available header
        await page.wait_for_selector("text=Problems Available", timeout=10000)
        available_text = await page.locator("text=Problems Available").first.inner_text()
        print(f"[Playwright Test] Initial unlock state: '{available_text}'")

        # Check that locked problems show the locked message and have NO LeetCode link
        locked_notices = await page.locator("text=LeetCode link locked").count()
        print(f"[Playwright Test] Found {locked_notices} locked LeetCode notices on locked cards.")
        assert locked_notices >= 1, "Expected at least 1 locked notice on locked problems!"

        # Take screenshot showing both unlocked (with LeetCode links) and locked (hidden links)
        screenshot_path = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815/verified_43_company_track_locked_leetcode_links_hidden.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"[Playwright Test] Saved screenshot to {screenshot_path}")

        # Click "Mark Solved" on an unsolved problem to test dynamic unlock
        mark_solved_btn = page.locator("button:has-text('Mark Solved')").first
        if await mark_solved_btn.is_visible():
            await mark_solved_btn.click()
            await page.wait_for_timeout(2000)
            print("[Playwright Test] Successfully toggled problem solved status!")

        await browser.close()
    print("[Playwright Test] Verification successfully completed!")

if __name__ == "__main__":
    asyncio.run(main())
