import os
import asyncio
from playwright.async_api import async_playwright, BrowserContext
from bu_agent_sdk.tools import tool

_ctx: BrowserContext | None = None
_pw = None
_PROFILE = os.path.expanduser("~/.jarvis/youtube-profile")


async def _browser() -> BrowserContext:
    global _ctx, _pw
    if _ctx is None:
        print("[MUSIC] launching browser...")
        os.makedirs(_PROFILE, exist_ok=True)
        _pw = await async_playwright().start()
        _ctx = await _pw.chromium.launch_persistent_context(
            _PROFILE,
            headless=False,
            args=["--no-first-run", "--no-default-browser-check", "--autoplay-policy=no-user-gesture-required"],
        )
        print("[MUSIC] browser ready")
    return _ctx


async def _page():
    ctx = await _browser()
    return ctx.pages[0] if ctx.pages else await ctx.new_page()


@tool("Play music on YouTube. Accepts a song or artist name to search for.")
async def play_music(query: str = "") -> str:
    print(f"[MUSIC] play_music called: {query!r}")
    try:
        page = await _page()
    except Exception as e:
        print(f"[MUSIC] browser launch failed: {e}")
        return f"Browser error: {e}"
    print(f"[MUSIC] page ready, url={page.url!r}")
    await page.bring_to_front()

    if query:
        encoded = query.replace(" ", "+")
        await page.goto(
            f"https://www.youtube.com/results?search_query={encoded}",
            wait_until="domcontentloaded",
        )
        try:
            video = page.locator("ytd-video-renderer a#thumbnail").first
            await video.wait_for(timeout=10_000)
            await video.click()
            print(f"[MUSIC] clicked first video")
        except Exception as e:
            print(f"[MUSIC] click error: {e}")
            return f"Opened YouTube — searching for {query}."
        return f"Playing {query} on YouTube."
    else:
        await page.goto("https://www.youtube.com", wait_until="domcontentloaded")
        return "Opened YouTube."


@tool("Pause or resume music")
async def pause_music() -> str:
    try:
        page = await _page()
        await page.keyboard.press("k")
        return "Toggled play/pause."
    except Exception as e:
        return f"Could not pause: {e}"


@tool("Go to the previous track")
async def previous_track() -> str:
    try:
        page = await _page()
        await page.go_back()
        return "Went back."
    except Exception as e:
        return f"Could not go back: {e}"


@tool("Skip to the next track")
async def next_track() -> str:
    try:
        page = await _page()
        btn = page.locator(".ytp-next-button")
        if await btn.count():
            await btn.click()
            return "Skipped to next."
        return "No next track available."
    except Exception as e:
        return f"Could not skip: {e}"


@tool("Set volume. Level 0-100")
async def set_volume(level: int) -> str:
    if level < 0 or level > 100:
        return "Volume level must be between 0 and 100."
    try:
        page = await _page()
        await page.evaluate(f"""
            (() => {{
                const video = document.querySelector('video');
                if (video) video.volume = {level / 100};
            }})()
        """)
        return f"Set volume to {level}."
    except Exception as e:
        return f"Could not set volume: {e}"


@tool("Get the current track info")
async def current_track_info() -> str:
    try:
        page = await _page()
        title = await page.locator("h1.ytd-watch-metadata yt-formatted-string").text_content(timeout=5_000)
        return f"Currently playing: {title.strip()}."
    except Exception as e:
        return f"Could not get track info: {e}"
