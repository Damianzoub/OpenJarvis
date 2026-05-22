import json
import os
from typing import AsyncGenerator

from bu_agent_sdk import Agent
from bu_agent_sdk.agent import FinalResponseEvent, ToolCallEvent
from bu_agent_sdk.llm.openai.like import ChatOpenAILike

from agent.filesystem_agent import make_filesystem_agent
from agent.email_agent import make_gmail_agent
from agent.calendar_agent import make_agenda_agent
from agent.weather_agent import make_weather_agent
from agent.news_agent import make_news_agent
from agent.music_agent import make_music_agent

from prompts.router_prompt import _ROUTER_PROMPT


def _make_llm() -> ChatOpenAILike:
    return ChatOpenAILike(
        model="qwen2.5:7b",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )


async def _classify(user_message: str) -> str:
    agent = Agent(llm=_make_llm(), tools=[], system_prompt=_ROUTER_PROMPT)
    result = await agent.query(user_message)
    return result.strip().lower()


async def stream(user_message: str) -> AsyncGenerator[str, None]:
    yield json.dumps({"type": "status", "content": "Thinking..."})

    agent_name = await _classify(user_message)
    print(f"[DEBUG] routed to: {agent_name}")

    if agent_name == "filesystem":
        agent = make_filesystem_agent()
    elif agent_name == "email":
        agent = make_gmail_agent()
    elif agent_name == "calendar":
        agent = make_agenda_agent()
    elif agent_name == "weather":
        agent = make_weather_agent()
    elif agent_name == "news":
        agent = make_news_agent()
    elif agent_name == "music":
        agent = make_music_agent()
    else:
        agent = Agent(llm=_make_llm(), tools=[], system_prompt="You are Jarvis, an AI desktop assistant. Answer the user's question helpfully and concisely.")

    async for event in agent.query_stream(user_message):
        if isinstance(event, ToolCallEvent):
            yield json.dumps({"type": "tool", "content": f"Using {event.tool}..."})
        elif isinstance(event, FinalResponseEvent):
            yield json.dumps({"type": "text", "content": event.content})

    yield json.dumps({"type": "done"})
