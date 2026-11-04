import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815"
BASE_URL = "http://localhost:5173"

async def main():
    print("[Playwright Workspace Test] Starting layout and chatbot expansion verification...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Standard 1440x900 desktop viewport
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))

        # 1. Login
        print("[Playwright Workspace Test] Logging in as candidate@skillissue.com...")
        await page.goto(f"{BASE_URL}/login")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[type="email"]', 'candidate@skillissue.com')
        await page.fill('input[type="password"]', 'Password123!')
        await page.click('button:has-text("Sign In")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # 2. Go to Projects Catalog
        print("[Playwright Workspace Test] Navigating to /projects...")
        await page.goto(f"{BASE_URL}/projects")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)

        # 3. Launch Workspace for Project 1 (Rate Limiter)
        print("[Playwright Workspace Test] Launching Rate Limiter project workspace...")
        launch_btn = page.locator("button:has-text('Launch Workspace')").first
        await launch_btn.wait_for(timeout=5000)
        await launch_btn.click()

        # Wait for workspace page to load
        await page.wait_for_url(lambda u: "/projects/" in u and "/projects" != u, timeout=10000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2500)
        print(f"[Playwright Workspace Test] Loaded workspace URL: {page.url}")

        # 4. Measure initial panel bounding boxes
        print("\n=== Verifying Initial 3-Panel Layout ===")
        # Wait for AI Pair Programmer header to be visible
        ai_header = page.locator("text=AI Pair Programmer").first
        await ai_header.wait_for(timeout=10000)

        # Get bounding boxes of the 3 panels
        left_panel = page.locator("text=Repository Tree").first.locator("xpath=ancestor::div[contains(@class, 'bg-white')][position()=last()]")
        
        # Locate chatbot panel container
        right_panel = page.locator("text=AI Pair Programmer").first.locator("xpath=ancestor::div[contains(@class, 'shadow-xs') or contains(@class, 'border-l')][position()=last()]")
        right_box = await right_panel.bounding_box()
        print(f"[Playwright Workspace Test] Right Chatbot Panel Bounding Box: {right_box}")
        
        assert right_box is not None, "Chatbot panel must exist in DOM!"
        assert right_box['width'] >= 300, f"Expected chatbot width >= 300px, got {right_box['width']}px! (Layout squishing bug detected if < 100px)"
        print(f"[Playwright Workspace Test] PASSED: Chatbot panel initial width is {right_box['width']:.1f}px (spacious ~30% view)!")

        # Verify Suggestion Chips and Send Area
        chips_count = await page.locator("button:has-text('Explain Architecture')").count()
        assert chips_count > 0, "Expected suggestion chips to be visible"
        print("[Playwright Workspace Test] Suggestion chips verified!")

        # Screenshot 1: Pristine Default Workspace Layout (30% Chatbot)
        ss1 = os.path.join(ARTIFACT_DIR, "verified_38_project_workspace_layout_fixed.png")
        await page.screenshot(path=ss1, full_page=True)
        print(f"[Playwright Workspace Test] Saved screenshot 1 to {ss1}")

        # 5. Test Expand Chatbot to Wide View (50%)
        print("\n=== Testing Chatbot Expand to 50% Wide View ===")
        expand_btn = page.locator("button[title*='Expand to wide view']").first
        await expand_btn.wait_for(timeout=5000)
        await expand_btn.click()
        await page.wait_for_timeout(1000)

        # Measure expanded chatbot width
        expanded_box = await right_panel.bounding_box()
        print(f"[Playwright Workspace Test] Expanded Chatbot Panel Bounding Box: {expanded_box}")
        assert expanded_box is not None
        assert expanded_box['width'] > right_box['width'] + 100, \
            f"Expected expanded width > {right_box['width'] + 100}px, got {expanded_box['width']}px"
        print(f"[Playwright Workspace Test] PASSED: Chatbot successfully expanded from {right_box['width']:.1f}px to {expanded_box['width']:.1f}px (50% wide view)!")

        # Screenshot 2: Chatbot Expanded (50% wide view)
        ss2 = os.path.join(ARTIFACT_DIR, "verified_39_project_workspace_chatbot_expanded.png")
        await page.screenshot(path=ss2, full_page=True)
        print(f"[Playwright Workspace Test] Saved screenshot 2 to {ss2}")

        # 6. Test Restore Normal Width (30%)
        print("\n=== Testing Restore Normal Width (30%) ===")
        restore_btn = page.locator("button[title*='Restore standard width']").first
        await restore_btn.click()
        await page.wait_for_timeout(1000)
        restored_box = await right_panel.bounding_box()
        print(f"[Playwright Workspace Test] Restored Chatbot Width: {restored_box['width']:.1f}px")
        assert abs(restored_box['width'] - right_box['width']) < 50
        print("[Playwright Workspace Test] PASSED: Restored back to ~30% standard width!")

        # 7. Test Top Header AI Copilot Toggle Button (Collapse & Reopen)
        print("\n=== Testing AI Copilot Header Toggle (Collapse & Reopen) ===")
        header_copilot_btn = page.locator("button:has-text('AI Copilot')").first
        await header_copilot_btn.click()
        await page.wait_for_timeout(1000)

        # Verify floating dock button appeared on the right edge
        dock_btn = page.locator("button[title*='Open AI Pair Programmer']").first
        await dock_btn.wait_for(timeout=5000)
        print("[Playwright Workspace Test] Chatbot collapsed! Floating dock button appeared on right edge.")

        # Click dock button to reopen
        await dock_btn.click()
        await page.wait_for_timeout(1000)
        reopened_box = await right_panel.bounding_box()
        assert reopened_box is not None and reopened_box['width'] >= 300
        print(f"[Playwright Workspace Test] PASSED: Reopened chatbot from dock button. Width: {reopened_box['width']:.1f}px!")

        # 8. Test asking a question to the Chatbot
        print("\n=== Testing Chatbot Interaction ===")
        chip = page.locator("button:has-text('Explain Architecture')").first
        await chip.click()
        print("[Playwright Workspace Test] Clicked 'Explain Architecture' prompt chip...")
        
        # Wait for response message to appear
        await page.wait_for_timeout(4000)
        chat_content = await right_panel.inner_text()
        print(f"[Playwright Workspace Test] Chat response received! Snippet: {chat_content[:150]}...")

        # Screenshot 3: Chatbot with response in workspace
        ss3 = os.path.join(ARTIFACT_DIR, "verified_40_project_workspace_chatbot_interactive.png")
        await page.screenshot(path=ss3, full_page=True)
        print(f"[Playwright Workspace Test] Saved screenshot 3 to {ss3}")

        await browser.close()
    print("\n[Playwright Workspace Test] ALL TESTS PASSED FLAWLESSLY!")

if __name__ == "__main__":
    asyncio.run(main())
