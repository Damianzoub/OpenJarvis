from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from tools.growth import log_goal, log_progress, list_goals
from prompts.growth_prompt import GROWTH_PROMPT
from prompts.langfuse_client import get_prompt

def make_growth_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434",
            temperature=0.1
        ),
        tools=[log_goal, log_progress, list_goals],
        system_prompt=get_prompt(name="growth_prompt") or GROWTH_PROMPT,
    )
