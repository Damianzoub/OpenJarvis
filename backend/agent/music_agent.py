from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from tools.music import *
from prompts.music_prompt import MUSIC_PROMPT

def make_music_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434"
        ),
        tools=[play_music, pause_music, previous_track, next_track, set_volume, current_track_info],
        system_prompt=MUSIC_PROMPT
    )

