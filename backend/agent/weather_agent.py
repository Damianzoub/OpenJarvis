import os 
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from tools.weather import get_weather

from prompts.weather_prompt import WEATHER_PROMPT
from prompts.langfuse_client import get_prompt
def make_weather_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434",
            temperature=0.1
        ),
        tools=[get_weather],
        system_prompt=get_prompt(name="weather_prompt") or WEATHER_PROMPT,
    )