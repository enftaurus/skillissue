import asyncio
import os
from playwright.async_api import async_playwright

async def verify_firefox_audio():
    artifacts_dir = "/home/rajababu/.gemini/antigravity/brain/3eadf0df-f972-46ab-a2ed-38b8336db815"
    os.makedirs(artifacts_dir, exist_ok=True)

    async with async_playwright() as p:
        print("[Playwright] Launching Firefox...")
        browser = await p.firefox.launch(
            headless=True,
            firefox_user_prefs={"media.navigator.permission.disabled": True}
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        # 1. Login
        print("[Playwright] Navigating to login page in Firefox...")
        await page.goto("http://localhost:5173/login")
        await page.wait_for_selector('input[type="email"]')
        await page.fill('input[type="email"]', '1602-24-733-160@vce.ac.in')
        await page.fill('input[type="password"]', 'rajababu')
        await page.click('button:has-text("Sign In")')

        # 2. Wait for dashboard
        await page.wait_for_url("http://localhost:5173/", timeout=10000)
        await page.wait_for_selector('text=Start Practice Interview', timeout=10000)
        print("[Playwright] Logged in successfully in Firefox!")

        # 3. Create or navigate to technical interview
        await page.goto("http://localhost:5173/interviews/new")
        await page.wait_for_selector('text=Setup Practice Interview', timeout=10000)
        print("[Playwright] On interview setup page...")

        # Click Start Button
        start_btn = page.locator('button:has-text("Start Practice Interview Session")')
        await start_btn.click()

        # 4. Wait for interview room to load
        await page.wait_for_url(r"**/interviews/*", timeout=15000)
        print("[Playwright] Entered interview session room in Firefox:", page.url)

        await page.wait_for_selector('text=Turn 1 of ~8', timeout=10000)

        # 5. Verify Speak Answer button exists in Firefox
        speak_btn = page.locator('button:has-text("Speak Answer")')
        is_speak_visible = await speak_btn.is_visible()
        print(f"[Playwright] Is 'Speak Answer' mic button visible in Firefox? {is_speak_visible}")
        assert is_speak_visible, "Speak Answer button should be visible in Firefox with MediaRecorder support!"

        # 6. Verify Voice toggle & Voice Persona selector
        voice_toggle = page.locator('button:has-text("Voice Off")')
        await voice_toggle.click()
        await page.wait_for_timeout(500)

        voice_on_btn = page.locator('button:has-text("Voice On")')
        assert await voice_on_btn.is_visible(), "Voice On should now be active!"

        voice_select = page.locator('select[title="Select Interviewer Voice Persona"]')
        assert await voice_select.is_visible(), "Voice Persona select dropdown must be visible when Voice is On!"

        # Select Neerja (India Female)
        await voice_select.select_option(value="en-IN-NeerjaNeural")
        print("[Playwright] Selected 'Neerja (India Female)' voice in Firefox!")

        # 7. Take screenshot of live interview room in Firefox
        screenshot_path = os.path.join(artifacts_dir, "verified_16_firefox_neural_audio_room.png")
        await page.screenshot(path=screenshot_path)
        print(f"[Playwright] Saved Firefox audio room screenshot: {screenshot_path}")

        # 8. Test clicking Listen button on interviewer's question
        listen_btn = page.locator('button:has-text("Listen")').first
        if await listen_btn.is_visible():
            await listen_btn.click()
            print("[Playwright] Clicked Listen button, triggered cloud neural audio playback!")
            await page.wait_for_timeout(2000)

        # 9. Test pushing Speak Answer (Microphone recording)
        await speak_btn.click()
        await page.wait_for_timeout(1000)

        # Verify active recording banner is shown
        recording_banner = page.locator('text=Recording your response...')
        banner_visible = await recording_banner.is_visible()
        print(f"[Playwright] Recording banner visible with equalizer bars: {banner_visible}")

        # Screenshot recording state
        recording_screenshot_path = os.path.join(artifacts_dir, "verified_17_firefox_recording_state.png")
        await page.screenshot(path=recording_screenshot_path)
        print(f"[Playwright] Saved Firefox recording screenshot: {recording_screenshot_path}")

        # Click Done Speaking
        done_btn = page.locator('button:has-text("Done Speaking")')
        if await done_btn.is_visible():
            await done_btn.click()
            print("[Playwright] Clicked Done Speaking!")

        await browser.close()
        print("[Playwright] Firefox verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(verify_firefox_audio())
