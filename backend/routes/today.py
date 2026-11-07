import json
from datetime import datetime
from zoneinfo import ZoneInfo

import redis.asyncio as redis
from fastapi import APIRouter
from pydantic import BaseModel
today_router = APIRouter(prefix="/today", tags=["today"])
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
ATHENS = ZoneInfo("Europe/Athens")


class Thing(BaseModel):
    time: str
    title: str


@today_router.get("", response_model=list[Thing])
async def todays_things():
    events = json.loads(await r.get("today_events") or "[]")
    things = []
    for e in events:
        start = e.get("start", {})
        if "dateTime" in start:
            time = datetime.fromisoformat(start["dateTime"]).astimezone(ATHENS).strftime("%H:%M")
        else:
            time = "All day"
        things.append({"time": time, "title": e.get("summary", "Untitled")})
    return things
