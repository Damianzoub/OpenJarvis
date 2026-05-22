from bu_agent_sdk.agent import Agent
from bu_agent_sdk.llm.openai.like import ChatOpenAILike
from tools.music import *
from prompts.music_prompt import MUSIC_PROMPT

def make_music_agent():
    return Agent(
        llm=ChatOpenAILike(
            model="qwen2.5:7b",
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        ),
        tools=[play_music, pause_music, previous_track, next_track, set_volume, current_track_info],
        system_prompt=MUSIC_PROMPT
    )

