from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from tools.search_files import search_files, read_file
from tools.open_app import open_app

import os
from dotenv import load_dotenv

load_dotenv()

FILESYSTEM_PROMPT = (
    "You are a file system assistant. "
    "You MUST use your tools to answer — never write code or explain how to do it. "
    "To find files: call search_files. To read or check a specific file: call read_file. "
    "To open an app: call open_app."
)

def make_filesystem_agent():
    if os.getenv("ENV") == "Prod":
        api_key = os.getenv("OPENAI_API_KEY") or None
        if api_key is None:
            raise ValueError("We don't have an API KEY")
        llm = ChatOpenAI(model="gpt-6-luna",api_key=api_key,temperature=0.1)
    else:
        llm = ChatOllama(model="qwen2.5:7b",temperature=0.1)
    return create_agent(model=llm,tools=[search_files, read_file, open_app],system_prompt=FILESYSTEM_PROMPT)
