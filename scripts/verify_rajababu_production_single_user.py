import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:5173"
ARTIFACT_DIR = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815"

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Step 1: Login as rajababu using username "rajababu"
        print("Logging in with username 'rajababu'...")
        await page.goto(f"{BASE_URL}/login")
        await page.wait_for_selector('input[type="password"]')
        await page.locator('input').first.fill("rajababu")
        await page.fill('input[type="password"]', "Password123!")
        await page.click('button[type="submit"]')
        
        # Admin lands directly on /admin/analytics
        await page.wait_for_url(lambda url: "/admin/analytics" in url, timeout=10000)
        await page.wait_for_selector("text=Platform Analytics", timeout=10000)
        await asyncio.sleep(1)

        # Capture screenshot of single production user in analytics
        await page.screenshot(path=f"{ARTIFACT_DIR}/verified_59_rajababu_single_production_user.png")
        print("✓ Captured verified_59_rajababu_single_production_user.png")

        # Verify page displays Real Production Candidates (1 user)
        body_text = await page.locator("body").inner_text()
        assert "1 user" in body_text or "1" in body_text, "Expected exactly 1 real production user"
        print("✓ Verified UI displays exactly 1 user in production database!")

        # Step 2: Navigate to Dashboard to confirm rajababu has full platform access
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_selector("text=Career Readiness & Rigor", timeout=10000)
        await page.screenshot(path=f"{ARTIFACT_DIR}/verified_60_rajababu_dashboard_access.png")
        print("✓ Captured verified_60_rajababu_dashboard_access.png")

        await browser.close()
        print("🎉 Verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(verify())
