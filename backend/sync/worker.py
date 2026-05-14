import asyncio 
from sync.gmail import sync_recent_emails
from sync.calendar import sync_today_events

async def start_background_tasks():
    while True:
        try:
            await sync_recent_emails()
            await sync_today_events()
        except Exception as e:
            print(f"Error during sync: {e}")
        await asyncio.sleep(10)  # Wait for 5 minutes before next sync
