from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from tools.calendar import list_events, create_event
from prompts.calendar_prompt import get_calendar_prompt

def make_agenda_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434"
        ),
        tools=[list_events, create_event],
        system_prompt=get_calendar_prompt(),
    )

