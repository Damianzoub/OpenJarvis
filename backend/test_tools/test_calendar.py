import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timezone 
from googleapiclient.discovery import build 
from auth.google_auth import get_credentials
from tools.calendar import GoogleCalendarAdapter


async def main():
    service = build("calendar", "v3", credentials=get_credentials())
    cal = GoogleCalendarAdapter(service)

    now = datetime.now(timezone.utc).isoformat()
    week_end = now.replace(now[:10], now[:8] + str(int(now[8:10]) + 7).zfill(2))

    from datetime import timedelta
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=7)

    events = await cal.list_events(start=start.isoformat(), end=end.isoformat())
    if not events:
        print("No events found.")
    else:
        print("Upcoming events:")
        for event in events:
            print(f"{event['title']} at {event['start']}")

asyncio.run(main())