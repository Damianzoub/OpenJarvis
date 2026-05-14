import os 
from bu_agent_sdk.agent import Agent
from bu_agent_sdk.llm.openai.like import ChatOpenAILike
from tools.search_files import search_files
from tools.open_app import open_app


def make_filesystem_agent() -> Agent:
    return Agent(
        llm=ChatOpenAILike(
            model="qwen2.5:7b",
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        ),
        tools=[search_files, open_app],
        system_prompt=(
            "You are a file system assistant. "
            "You MUST use your tools to answer — never write code or explain how to do it. "
            "To find files: call search_files. To open an app: call open_app."
        ),
    )