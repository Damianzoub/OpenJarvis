import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bu_agent_sdk.agent import FinalResponseEvent, ToolCallEvent, ToolResultEvent
from agent.filesystem_agent import make_filesystem_agent


async def main():
    agent = make_filesystem_agent()
    async for event in agent.query_stream("Find all .py files in /Users/damianoszoumpos/OpenJarvis/backend/agent"):
        if isinstance(event, ToolCallEvent):
            print(f"[TOOL CALL] {event.tool} → {event.args}")
        elif isinstance(event, ToolResultEvent):
            print(f"[TOOL RESULT] {event.result[:200]}")
        elif isinstance(event, FinalResponseEvent):
            print(f"[FINAL] {event.content}")


asyncio.run(main())
