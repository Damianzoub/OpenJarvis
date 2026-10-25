from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from tools.calendar import list_events, create_event
from prompts.calendar_prompt import get_calendar_prompt
from datetime import datetime,timezone,timedelta
from prompts.langfuse_client import get_prompt

def make_agenda_agent():
    athens = timezone(timedelta(hours=3))
    now = datetime.now(athens)
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434",
            temperature=0.1
        ),
        tools=[list_events, create_event],
        system_prompt=get_prompt(name="calendar_prompt",today_str=today_str,tomorrow_str=tomorrow_str) or get_calendar_prompt(),
    )

