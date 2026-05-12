import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Searching YouTube...")
        await page.goto("https://www.youtube.com/results?search_query=Never+Gonna+Give+You+Up+Rick+Astley")

        print("Clicking first video...")
        await page.wait_for_selector("ytd-video-renderer #video-title")
        await page.locator("ytd-video-renderer #video-title").first.click()

        print("Playing!")
        await asyncio.sleep(300)
        await browser.close()


asyncio.run(main())
