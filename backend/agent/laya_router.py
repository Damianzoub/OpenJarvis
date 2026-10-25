import asyncio
import time

import laya

from observability.logger import logger
from observability.metrics import record_call

agent_router=None

AGENT_CRITERIA = {
    "Filesystem": "find, search, read or manage files on the computer",
    "Email": "read, search or send email",
    "Calendar": "check availability, list or create calendar events",
    "Weather": "weather forecast or current conditions",
    "News": "news headlines or current events",
    "Music": "play, pause or choose music",
    "Knowledge": "what the user wrote, saved or noted: their notes, documents, bio, projects, thesis",
    "Reminders": "set, list or cancel a reminder or task",
    "Growth": "personal goals, habits and self-improvement tracking",
    "Finance": "stock tickers like NVDA or AAPL, share prices, markets, budget and expenses",
    "General": "casual conversation, greetings, trivia and simple FAQ",
}

QUESTIONS = {
    "agent":{
        "type":"choice",
        "instructions":"which assistant domain should handle `request`?",
        "criteria":AGENT_CRITERIA
    }
}

# Splitting the 11 agents into groups of 4 and picking finalists routed 84% correctly on
# 50 labeled requests vs 64% for one flat 11-way choice (~210ms vs ~100ms per request).
GROUP_SIZE = 4

def _decide(user_message:str)->str:
    result = laya.predict_tournament(agent_router, user_message, QUESTIONS, group_size=GROUP_SIZE)
    return result["answers"]["agent"]["choice"]

def load_router()->None:
    global agent_router
    agent_router = laya.load("convaiinnovations/laya")
    _decide("hello")

async def route(user_message:str)->str:
    return await asyncio.to_thread(_decide, user_message)