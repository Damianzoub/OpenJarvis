from bu_agent_sdk import Agent
from bu_agent_sdk.llm.openai.like import ChatOpenAILike
from tools.calendar import list_events, create_event
from prompts.calendar_prompt import get_calendar_prompt

def make_agenda_agent():
    return Agent(
        llm=ChatOpenAILike(
            model="qwen2.5:7b",
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        ),
        tools=[list_events, create_event],
        system_prompt=get_calendar_prompt(),
    )

