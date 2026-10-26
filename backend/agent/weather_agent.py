from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from prompts.langfuse_client import get_prompt
from prompts.weather_prompt import WEATHER_PROMPT
from tools.weather import get_weather

import os
from dotenv import load_dotenv

load_dotenv()

def make_weather_agent():
    if os.getenv("ENV") == "Prod":
        api_key = os.getenv("OPENAI_API_KEY") or None
        if api_key is None:
            raise ValueError("We don't have an API KEY")
        llm = ChatOpenAI(model="gpt-6-luna",api_key=api_key,temperature=0.1)
    else:
        llm = ChatOllama(model="qwen2.5:7b",temperature=0.1)
    return create_agent(model=llm,tools=[get_weather],system_prompt=get_prompt(name="weather_prompt") or WEATHER_PROMPT)
