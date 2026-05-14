import json 
import asyncio
import redis 
from datetime import datetime, timedelta,timezone
from auth.google_auth import get_credentials
from googleapiclient.discovery import build

r = redis.Redis(host='localhost',port=6379,decode_responses=True)

def _service():
    return build("calendar", "v3", credentials=get_credentials())

async def sync_today_events():
    service = await asyncio.to_thread(_service)
    now = datetime.now(timezone.utc)
    end_of_day = now.replace(hour=23, minute=59, second=59)

    events_result = await asyncio.to_thread(
        lambda: service.events().list(
            calendarId='primary',
            timeMin=now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            timeMax=end_of_day.strftime('%Y-%m-%dT%H:%M:%SZ'),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
    )
    
    events = events_result.get('items', [])
    r.set('today_events', json.dumps(events))
    print(f"Synced {len(events)} today's events to Redis.")

