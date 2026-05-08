import json
import os
from typing import AsyncGenerator

from bu_agent_sdk import Agent
from bu_agent_sdk.agent import FinalResponseEvent, ToolCallEvent
from bu_agent_sdk.llm.openai.like import ChatOpenAILike

from agent.filesystem_agent import make_filesystem_agent
from prompts.router_prompt import _ROUTER_PROMPT


def _make_llm() -> ChatOpenAILike:
    return ChatOpenAILike(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
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

    if agent_name == "filesystem":
        agent = make_filesystem_agent()
    else:
        agent = Agent(llm=_make_llm(), tools=[])

    async for event in agent.query_stream(user_message):
        if isinstance(event, ToolCallEvent):
            yield json.dumps({"type": "tool", "content": f"Using {event.tool}..."})
        elif isinstance(event, FinalResponseEvent):
            yield json.dumps({"type": "text", "content": event.content})

    yield json.dumps({"type": "done"})
