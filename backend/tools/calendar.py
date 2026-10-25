import asyncio
from datetime import datetime
from textwrap import dedent
from guardrails import Guard, Validator, register_validator
from guardrails.errors import ValidationError
from guardrails.validator_base import FailResult, PassResult

def escape_applescript(value:str)->str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


@register_validator(name="valid-calendar-datetime", data_type="string")
class ValidCalendarDatetime(Validator):
    def validate(self, value, metadata):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return FailResult(error_message=f"'{value}' is not a valid ISO datetime.")
        return PassResult()


_guard = Guard().use(ValidCalendarDatetime())


class MacCalendarAdapter:
    async def create_event(
        self,
        title,
        start_date,
        end_date,
        calendar_name="Home"
    ):
        title = escape_applescript(title)
        start_date = escape_applescript(start_date)
        end_date = escape_applescript(end_date)
        calendar_name = escape_applescript(calendar_name)

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
from langchain.tools import tool
from auth.google_auth import get_credentials
from datetime import datetime, timedelta, timezone

from observability.logger import logger, DANGER

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


async def _delete_event(event_id: str):
    cal = _google_cal()
    return await cal.delete_event(event_id)

@tool(description="List upcoming calendar events for the next N days.")
async def list_events(days:int=7)->str:
    cached = redis_client.get("today_events")
    if cached:
        events = json.loads(cached)
        if events:
            return "\n".join([f"{e['summary']} at {e['start'].get('dateTime', e['start'].get('date'))}" for e in events])
    return await _list_events(days=days)

@tool(description="Create a calendar event with a title, start time, and end time.")
async def create_event(title:str, start:str, end:str)->str:
    try:
        _guard.validate(start)
        _guard.validate(end)
    except ValidationError as e:
        return str(e)

    if datetime.fromisoformat(end.replace("Z", "+00:00")) <= datetime.fromisoformat(start.replace("Z", "+00:00")):
        return "Invalid event: end time must be after start time."

    print(f"[CALENDAR] create_event called: {title!r} {start} -> {end}")
    result = await _create_event(title, start, end)
    redis_client.delete("today_events")
    return result


@tool(description="Delete a calendar event by its id. Destructive — always ask the user to confirm before calling this with confirm=True; call it once with confirm=False first to preview.")
async def delete_event(event_id: str, confirm: bool = False) -> str:
    if not confirm:
        return f"This will permanently delete event {event_id}. Call delete_event again with confirm=True to proceed."

    logger.log(DANGER, f"calendar event deleted: {event_id}")
    await _delete_event(event_id)
    redis_client.delete("today_events")
    return f"Event {event_id} deleted."
