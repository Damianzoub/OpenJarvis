import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from langchain_core.messages import AIMessage, ToolMessage
from agent.filesystem_agent import make_filesystem_agent


async def main():
    agent = make_filesystem_agent()
    state = {
        "messages": [
            {"role": "user", "content": "Find all .py files in /Users/damianoszoumpos/OpenJarvis/backend/agent"}
        ]
    }
    async for chunk in agent.astream(state, stream_mode="values"):
        message = chunk["messages"][-1]
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                print(f"[TOOL CALL] {call['name']} → {call['args']}")
        elif isinstance(message, ToolMessage):
            print(f"[TOOL RESULT] {str(message.content)[:200]}")
        elif isinstance(message, AIMessage) and message.content:
            print(f"[FINAL] {message.content}")


asyncio.run(main())
