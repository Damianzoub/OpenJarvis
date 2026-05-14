import asyncio
from textwrap import dedent

def escape_applescript(value:str)->str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class MacCalendarAdapter:
    async def create_event(
        self,
        title,
        start_date,
        end_date,
        calendar_name="Home"
    ):
        script = dedent(f'''
        tell application "Calendar"
            tell calendar "{calendar_name}"
                make new event with properties {{
                    summary:"{title}",
                    start date:date "{start_date}",
                    end date:date "{end_date}"
                }}
            end tell
        end tell
        ''')

        process = await asyncio.create_subprocess_exec(
            "osascript",
            "-e",
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(stderr.decode())

        return stdout.decode()

    async def list_events(
            self,
            start_date,
            end_date,
            calendar_name="Home"
    ):
        calendar_name = escape_applescript(calendar_name)

        script = dedent(f'''
        tell application "Calendar"
            set output to ""
            tell calendar "{calendar_name}"
                set matchedEvents to every event whose start date ≥ date "{start_date}" and start date ≤ date "{end_date}"

                repeat with e in matchedEvents
                    set output to output & (uid of e) & "||" & (summary of e) & "||" & ((start date of e) as string) & "||" & ((end date of e) as string) & linefeed
                end repeat
            end tell
            return output
        end tell
        ''')

        raw = await self._run_applescript(script)

        events = []
        for line in raw.strip().splitlines():
            parts = line.split("||")
            if len(parts) == 4:
                events.append({
                    "id": parts[0],
                    "title": parts[1],
                    "start": parts[2],
                    "end": parts[3],
                    "provider": "mac",
                })

        return events
    
    async def delete_event(self,event_id,calendar_name="Home"):
        calendar_name = escape_applescript(calendar_name)
        event_id = escape_applescript(event_id)

        script = dedent(f'''
        tell application "Calendar"
            tell calendar "{calendar_name}"
                delete first event whose uid is "{event_id}"
            end tell
        end tell
        ''')

        await self._run_applescript(script)

        return {
            "deleted":True,
            "event_id":event_id,
            "provider":"mac"
        }

    async def _run_applescript(self,script):
        process = await asyncio.create_subprocess_exec(
            'osascript',
            '-e',
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout,stderr = await process.communicate()
        if process.returncode != 0:
            raise Exception(stderr.decode().strip())
        return stdout.decode().strip()

class GoogleCalendarAdapter:
    def __init__(self, service, timezone="Europe/Athens"):
        self.service = service
        self.timezone = timezone

    async def list_events(self, start, end, calendar_id="primary"):
        events = await asyncio.to_thread(
            lambda: self.service.events().list(
                calendarId=calendar_id,
                timeMin=start,
                timeMax=end,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
        )

        return [
            {
                "id": event["id"],
                "title": event.get("summary", "Untitled"),
                "start": event.get("start"),
                "end": event.get("end"),
                "provider": "google",
            }
            for event in events.get("items", [])
        ]

    async def create_event(self, title, start, end, calendar_id="primary"):
        event = {
            "summary": title,
            "start": {
                "dateTime": start,
                "timeZone": self.timezone,
            },
            "end": {
                "dateTime": end,
                "timeZone": self.timezone,
            },
        }

        return await asyncio.to_thread(
            lambda: self.service.events().insert(
                calendarId=calendar_id,
                body=event,
            ).execute()
        )

    async def delete_event(self, event_id, calendar_id="primary"):
        await asyncio.to_thread(
            lambda: self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
            ).execute()
        )

        return {
            "deleted": True,
            "event_id": event_id,
            "provider": "google",
        }






from googleapiclient.discovery import build 
from bu_agent_sdk.tools import tool 
from auth.google_auth import get_credentials
from datetime import datetime, timedelta, timezone

import redis 
import json 

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def _google_cal():
    service = build("calendar", "v3", credentials=get_credentials())
    return GoogleCalendarAdapter(service)

async def _list_events(days:int=7):
    cal = _google_cal()
    now = datetime.now(timezone.utc)
    start = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    end = (now + timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
    events = await cal.list_events(start=start, end=end)
    if not events:
        return "No events found."
    return "\n".join([f"{e['title']} at {e['start']}" for e in events])


async def _create_event(title:str, start:str, end:str):
    cal = _google_cal()
    event = await cal.create_event(title=title, start=start, end=end)
    return f"Event created: {event.get('htmlLink', 'No link available')}"

@tool("List upcoming calendar events from the user's Google Calendar. Call this when the user asks to list or show their events.")
async def list_events(days:int=7)->str:
    cached = redis_client.get("today_events")
    if cached:
        events = json.loads(cached)
        if not events:
            return "No events found."
        return "\n".join([f"{e['summary']} at {e['start'].get('dateTime', e['start'].get('date'))}" for e in events])
    return await _list_events(days=days)

@tool("Create a calendar event in the user's Google Calendar. Call this when the user asks to create an event.")
async def create_event(title:str, start:str, end:str)->str:
    return await _create_event(title, start, end)
