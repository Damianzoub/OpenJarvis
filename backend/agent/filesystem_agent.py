import os 
from bu_agent_sdk.tools import tool
from bu_agent_sdk.agent import Agent, TaskComplete
from bu_agent_sdk.llm.openai.like import ChatOpenAILike

from tools.search_files import search_files
from tools.open_app import open_app

@tool("Signal that the task is complete")
async def done(message:str)->str:
    raise TaskComplete(message)


def make_filesystem_agent() -> Agent:
    return Agent(
        llm=ChatOpenAILike(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        ),
        tools=[search_files, open_app, done],
        system_prompt=(
            "You are a file system assistant. "
            "You MUST use your tools to answer — never write code or explain how to do it. "
            "To find files: call search_files. To open an app: call open_app. "
            "When done, call done() with a short summary of what you did."
        ),
        require_done_tool=True
    )