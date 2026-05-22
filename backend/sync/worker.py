import asyncio
import httpx
from sync.gmail import sync_recent_emails
from sync.calendar import sync_today_events

_last_keepalive = 0.0

async def _keepalive_ollama() -> None:
    global _last_keepalive
    now = asyncio.get_event_loop().time()
    if now - _last_keepalive < 240:  # only ping every 4 minutes
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "qwen2.5:7b", "prompt": "", "keep_alive": "10m"},
            )
        _last_keepalive = now
    except Exception:
        pass

async def start_background_tasks():
    while True:
        try:
            await sync_recent_emails()
            await sync_today_events()
            await _keepalive_ollama()
        except Exception as e:
            print(f"Error during sync: {e}")
        await asyncio.sleep(30)
