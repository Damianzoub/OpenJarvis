import os 
from bu_agent_sdk.agent import Agent
from bu_agent_sdk.llm.openai.like import ChatOpenAILike
from tools.weather import get_weather

from prompts.weather_prompt import WEATHER_PROMPT

def make_weather_agent():
    return Agent(
        llm=ChatOpenAILike(
            model="qwen2.5:7b",
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        ),
        tools=[get_weather],
        system_prompt=WEATHER_PROMPT,
    )