from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from prompts.langfuse_client import get_prompt
from prompts.music_prompt import MUSIC_PROMPT
from tools.music import play_music, pause_music, previous_track, next_track, set_volume, current_track_info

import os
from dotenv import load_dotenv

load_dotenv()

def make_music_agent():
    if os.getenv("ENV") == "Prod":
        api_key = os.getenv("OPENAI_API_KEY") or None
        if api_key is None:
            raise ValueError("We don't have an API KEY")
        llm = ChatOpenAI(model="gpt-6-luna",api_key=api_key,temperature=0.1)
    else:
        llm = ChatOllama(model="qwen2.5:7b",temperature=0.1)
    return create_agent(model=llm,tools=[play_music, pause_music, previous_track, next_track, set_volume, current_track_info],system_prompt=get_prompt(name="music_prompt") or MUSIC_PROMPT)
