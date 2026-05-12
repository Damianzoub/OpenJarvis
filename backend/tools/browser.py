from playwright.async_api import async_playwright
import asyncio 
async def open_site(url:str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        page = await browser.new_page()

        await page.goto(f"https://{url}.com")

        await asyncio.sleep(300)


async def search(url:str,query:str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.fill("textarea",query)
        await page.press("textarea","Enter")
        await asyncio.sleep(300)

