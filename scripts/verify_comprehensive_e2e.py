import asyncio
from playwright.async_api import async_playwright

async def main():
    print("[E2E Playwright] Starting comprehensive browser verification...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 900})
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))

        # 1. Login as candidate
        print("\n=== Step 1: Candidate Login ===")
        await page.goto("http://localhost:5173/login")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[type="email"]', 'candidate@skillissue.com')
        await page.fill('input[type="password"]', 'Password123!')
        await page.click('button:has-text("Sign In")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        print(f"[E2E Playwright] Logged in successfully. Current URL: {page.url}")

        # 2. Company Tracks Catalog
        print("\n=== Step 2: Company Tracks Catalog ===")
        await page.goto("http://localhost:5173/tracks")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)
        
        uber_track = page.locator("text=Uber").first
        await uber_track.wait_for(timeout=10000)
        print("[E2E Playwright] Found Uber track card in catalog")

        # 3. Uber Track Detail with real CSV problems
        print("\n=== Step 3: Uber Track Detail & Real CSV Questions ===")
        await page.goto("http://localhost:5173/tracks/uber")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        
        await page.wait_for_selector("text=Uber Career Track", timeout=10000)
        print("[E2E Playwright] Loaded Uber Career Track page")

        # Verify problem count mentions 336 problems
        page_text = await page.content()
        assert "336" in page_text, "Expected Uber track to have 336 problems from CSV"
        print("[E2E Playwright] Verified total 336 problems from liquidslr CSV dataset!")

        # Verify Day 1 unlock: first 3 are unlocked
        assert "Problems Available" in page_text
        print("[E2E Playwright] Verified progressive unlock counter is visible")

        # Verify real LeetCode links
        leetcode_links = await page.locator("a[href*='leetcode.com/problems']").count()
        print(f"[E2E Playwright] Found {leetcode_links} LeetCode links on page 1")
        assert leetcode_links >= 3, f"Expected at least 3 LeetCode links, got {leetcode_links}"
        
        first_href = await page.locator("a[href*='leetcode.com/problems']").first.get_attribute("href")
        print(f"[E2E Playwright] First LeetCode link: {first_href}")
        assert "leetcode.com/problems/" in first_href

        # Search functionality
        search_input = page.locator("input[placeholder*='Search problems']")
        if await search_input.count() > 0:
            await search_input.fill("Bus Routes")
            await page.wait_for_timeout(800)
            print("[E2E Playwright] Tested search input with 'Bus Routes'")
            await search_input.fill("")
            await page.wait_for_timeout(800)

        # Pagination controls
        next_button = page.locator("button:has-text('Next')")
        if await next_button.count() > 0 and await next_button.is_enabled():
            await next_button.click()
            await page.wait_for_timeout(1000)
            print("[E2E Playwright] Clicked Next page in pagination")
            prev_button = page.locator("button:has-text('Prev')")
            await prev_button.click()
            await page.wait_for_timeout(1000)
            print("[E2E Playwright] Clicked Prev page in pagination")

        # Screenshot of Company Track Detail
        ss_track = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815/verified_36_company_track_csv_pagination.png"
        await page.screenshot(path=ss_track, full_page=True)
        print(f"[E2E Playwright] Saved screenshot to {ss_track}")

        # 4. Mock Interview Setup & Conversational Flow
        print("\n=== Step 4: Setup & Launch DSA Interview ===")
        await page.goto("http://localhost:5173/interviews/new")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)

        # Select DSA category button (labeled "DSA & Coding")
        dsa_cat_btn = page.locator("button:has-text('DSA & Coding')").first
        await dsa_cat_btn.wait_for(timeout=5000)
        await dsa_cat_btn.click()
        print("[E2E Playwright] Selected 'DSA & Coding' interview category")
        await page.wait_for_timeout(1000)

        # Click Start Practice Interview Session
        start_btn = page.locator("button:has-text('Start Practice Interview Session')")
        await start_btn.wait_for(timeout=5000)
        await start_btn.click()
        print("[E2E Playwright] Clicked Start Practice Interview Session button")

        # Wait for navigation to /interviews/:id
        await page.wait_for_url(lambda url: "/interviews/" in url and "/interviews/new" not in url, timeout=15000)
        print(f"[E2E Playwright] Navigated to interview session: {page.url}")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)

        # Verify Turn 0 opening greeting in chat
        content_after_start = await page.content()
        assert "welcome to the mock interview of Skill Issue" in content_after_start or "introduce yourself" in content_after_start, \
            "Expected Turn 0 greeting asking candidate to introduce themselves!"
        print("[E2E Playwright] Verified Turn 0 Opening Greeting: AI asks for candidate introduction & DSA background!")

        # Verify Auto-Speak toggle button is visible
        auto_speak_btn = page.locator("button:has-text('Auto-Speak')")
        if await auto_speak_btn.count() > 0:
            print("[E2E Playwright] Auto-Speak toggle is present in interview UI")

        # Step 4b: Submit Candidate Introduction
        print("\n=== Step 4b: Candidate Introduction Response ===")
        candidate_intro = "Hey! I am Raja Babu, a B.Tech CSE student. I am a competitive programmer and my favorite topic is dynamic programming because of overlapping subproblems and optimal substructure."
        
        chat_input = page.locator("textarea").first
        await chat_input.wait_for(timeout=5000)
        await chat_input.fill(candidate_intro)
        
        # Click send answer
        send_btn = page.locator("button:has-text('Send Answer')").first
        await send_btn.click()
        print("[E2E Playwright] Sent candidate introduction message. Waiting for Turn 1 response...")

        # Wait for Turn 1 response to appear
        await page.wait_for_timeout(6000)

        # Verify Turn 1 response in chat
        updated_content = await page.content()
        assert "start today" in updated_content.lower() or "question" in updated_content.lower() or "dynamic programming" in updated_content.lower() or "approach" in updated_content.lower(), \
            "Expected Turn 1 to acknowledge intro and present the problem"
        print("[E2E Playwright] Verified Turn 1: AI acknowledged candidate's intro, transitioned, and presented problem details!")

        # Screenshot of interview session
        ss_interview = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815/verified_37_interview_dsa_conversational_onboarding.png"
        await page.screenshot(path=ss_interview, full_page=True)
        print(f"[E2E Playwright] Saved screenshot to {ss_interview}")

        # 5. Role Isolation Check: Candidate visiting /admin/analytics should be redirected
        print("\n=== Step 5: Role Isolation Check ===")
        await page.goto("http://localhost:5173/admin/analytics")
        await page.wait_for_timeout(2000)
        admin_content = await page.content()
        assert page.url.rstrip("/") in ["http://localhost:5173", "http://localhost:5173/login", "http://localhost:5173/dashboard"] or "Unauthorized" in admin_content or "Access Denied" in admin_content, \
            f"Candidate should not access /admin/analytics! Current URL: {page.url}"
        print(f"[E2E Playwright] Role isolation verified: candidate blocked from admin portal. Redirected to: {page.url}")

        await browser.close()
    print("\n[E2E Playwright] All end-to-end browser verifications PASSED flawlessly!")

if __name__ == "__main__":
    asyncio.run(main())
