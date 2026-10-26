from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from prompts.langfuse_client import get_prompt
from prompts.calendar_prompt import get_calendar_prompt
from tools.calendar import list_events, create_event

from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

def make_agenda_agent():
    athens = timezone(timedelta(hours=3))
    now = datetime.now(athens)
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    if os.getenv("ENV") == "Prod":
        api_key = os.getenv("OPENAI_API_KEY") or None
        if api_key is None:
            raise ValueError("We don't have an API KEY")
        llm = ChatOpenAI(model="gpt-6-luna",api_key=api_key,temperature=0.1)
    else:
        llm = ChatOllama(model="qwen2.5:7b",temperature=0.1)
    return create_agent(model=llm,tools=[list_events, create_event],system_prompt=get_prompt(name="calendar_prompt",today_str=today_str,tomorrow_str=tomorrow_str) or get_calendar_prompt())
