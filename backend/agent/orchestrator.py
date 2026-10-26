from langgraph.graph import MessagesState
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from prompts.router_prompt import _ROUTER_PROMPT
from prompts.langfuse_client import get_prompt

import os
from dotenv import load_dotenv

load_dotenv()

GENERAL_PROMPT = "You are Jarvis, an AI desktop assistant. Answer the user's question helpfully and concisely. YOUR GOAL IS TO ANSWER SIMPLE FAQs and trivial questions"

def _make_llm():
    if os.getenv("ENV") == "Prod":
        api_key = os.getenv("OPENAI_API_KEY") or None
        if api_key is None:
            raise ValueError("We don't have an API KEY")
        return ChatOpenAI(model="gpt-6-luna",api_key=api_key,temperature=0.1)
    return ChatOllama(model="qwen2.5:7b",temperature=0.1)

def make_general_agent():
    return create_agent(model=_make_llm(),tools=[],system_prompt=GENERAL_PROMPT)


async def _classify(user_message: str) -> str:
    agent = create_agent(_make_llm(), tools=[], system_prompt= get_prompt(name="router_prompt") or _ROUTER_PROMPT)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": user_message}]})
    return result["messages"][-1].content.strip().lower()

async def route(user_message: str) -> str:
    decision = await _classify(user_message)
    if "filesystem" in decision:
        return "Filesystem"
    if "email" in decision:
        return "Email"
    if "calendar" in decision:
        return "Calendar"
    if "weather" in decision:
        return "Weather"
    if "news" in decision:
        return "News"
    if "music" in decision:
        return "Music"
    if "knowledge" in decision:
        return "Knowledge"
    if "reminders" in decision:
        return "Reminders"
    if "growth" in decision:
        return "Growth"
    if "finance" in decision:
        return "Finance"
    return "General"