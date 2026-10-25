from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from tools.music import *
from prompts.music_prompt import MUSIC_PROMPT
from prompts.langfuse_client import get_prompt
def make_music_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434",
            temperature=0.1
        ),
        tools=[play_music, pause_music, previous_track, next_track, set_volume, current_track_info],
        system_prompt=get_prompt(name="music_prompt") or MUSIC_PROMPT
    )

