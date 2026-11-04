import asyncio
from playwright.async_api import async_playwright
import httpx

async def main():
    print("[Playwright Test] Verifying Planly Reschedule to Today Feature...")
    
    # Check/ensure an active plan exists for candidate
    async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
        login_res = await client.post("/auth/login", json={"email": "candidate@skillissue.com", "password": "Password123!"})
        if login_res.status_code != 200:
            print("[Playwright Test] Creating candidate user...")
            await client.post("/auth/register", json={"email": "candidate@skillissue.com", "password": "Password123!"})
            login_res = await client.post("/auth/login", json={"email": "candidate@skillissue.com", "password": "Password123!"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check active plan
        active_plan_res = await client.get("/plans/active", headers=headers)
        if active_plan_res.status_code != 200 or not active_plan_res.json():
            print("[Playwright Test] Creating active plan for candidate...")
            await client.post("/plans/custom", headers=headers, json={
                "topic": "Dynamic Programming Mastery",
                "goal": "interview_prep",
                "daily_study_minutes": 45,
                "schedule_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "target_level": "intermediate"
            })
            active_plan_res = await client.get("/plans/active", headers=headers)
        
        plan = active_plan_res.json()
        print(f"[Playwright Test] Active plan: '{plan['title']}' with {len(plan['tasks'])} tasks.")

        # Ensure task 0 is completed and task 1 is not completed
        if len(plan["tasks"]) > 0 and not plan["tasks"][0]["is_completed"]:
            print("[Playwright Test] Marking task 1 as completed...")
            await client.post(f"/plans/tasks/{plan['tasks'][0]['id']}/toggle", headers=headers, json={"is_completed": True})

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 950})
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))

        # Log in via UI
        print("[Playwright Test] Logging in via UI...")
        await page.goto("http://localhost:5173/login")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[type="email"]', 'candidate@skillissue.com')
        await page.fill('input[type="password"]', 'Password123!')
        await page.click('button:has-text("Sign In")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)

        # Navigate to Planly
        print("[Playwright Test] Navigating to http://localhost:5173/planly...")
        await page.goto("http://localhost:5173/planly")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Verify Sprint header is present
        await page.wait_for_selector("text=Active Learning Sprint", timeout=10000)
        print("[Playwright Test] Active Learning Sprint loaded successfully.")

        # Check for Reschedule to Today button
        reschedule_btn = page.locator('button:has-text("Reschedule to Today")')
        await reschedule_btn.wait_for(state="visible", timeout=5000)
        print("[Playwright Test] 'Reschedule to Today' button found.")

        # Click Reschedule to Today
        await reschedule_btn.click()
        await page.wait_for_timeout(1000)

        # Verify Modal opened
        await page.wait_for_selector("text=Reschedule Sprint to Today", timeout=5000)
        await page.wait_for_selector("text=Completed (Preserved)", timeout=5000)
        await page.wait_for_selector("text=Remaining (Rescheduled)", timeout=5000)
        await page.wait_for_selector("text=TODAY", timeout=5000)
        print("[Playwright Test] Modal opened with preserved count and today's sequence verified!")

        # Screenshot 1: Modal Preview
        screenshot_modal_path = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815/verified_41_planly_reschedule_modal.png"
        await page.screenshot(path=screenshot_modal_path, full_page=False)
        print(f"[Playwright Test] Saved modal preview screenshot to {screenshot_modal_path}")

        # Click Confirm & Reschedule from Today
        confirm_btn = page.locator('button:has-text("Confirm & Reschedule from Today")')
        await confirm_btn.click()
        await page.wait_for_timeout(1500)

        # Verify success notification appears
        await page.wait_for_selector("text=Sprint successfully rescheduled starting today!", timeout=5000)
        print("[Playwright Test] Success banner confirmed!")

        # Screenshot 2: Rescheduled Sprint View
        screenshot_sprint_path = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815/verified_42_planly_rescheduled_active_sprint.png"
        await page.screenshot(path=screenshot_sprint_path, full_page=True)
        print(f"[Playwright Test] Saved rescheduled active sprint screenshot to {screenshot_sprint_path}")

        await browser.close()
        print("[Playwright Test] ALL ASSERTIONS PASSED! Planly Reschedule to Today verified end-to-end.")

if __name__ == "__main__":
    asyncio.run(main())
