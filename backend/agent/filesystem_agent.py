import os 

from tools.search_files import search_files, read_file
from tools.open_app import open_app
from langchain.agents import create_agent
from langchain_ollama import ChatOllama


def make_filesystem_agent():
    llm = ChatOllama(
        model="qwen2.5:7b",
        base_url="http://localhost:11434",
        temperature=0.1
    )
    tools = [search_files, read_file, open_app]
    system_prompt = (
        "You are a file system assistant. "
        "You MUST use your tools to answer — never write code or explain how to do it. "
        "To find files: call search_files. To read or check a specific file: call read_file. "
        "To open an app: call open_app."
    )
    
    return create_agent(llm, tools=tools, system_prompt=system_prompt)
    