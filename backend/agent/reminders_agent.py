from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from tools.reminders import add_reminder, list_reminders, complete_reminder
from prompts.reminders_prompt import REMINDERS_PROMPT
from prompts.langfuse_client import get_prompt

def make_reminders_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434",
            temperature=0.1
        ),
        tools=[add_reminder, list_reminders, complete_reminder],
        system_prompt=get_prompt(name="reminders_prompt") or REMINDERS_PROMPT,
    )
