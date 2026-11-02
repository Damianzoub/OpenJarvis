"""Quick check: can the agent's model drive browser-use? Prints the answer and how long it took.

ENV=Prod uses OpenAI (gpt-6-luna), otherwise local mistral:latest — same switch as the agents.
"""

import asyncio
import os
import time
from pathlib import Path

from browser_use import Agent, BrowserProfile
from browser_use.llm import ChatOllama, ChatOpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")

TASK = (
    "Go to https://news.ycombinator.com. Scroll down to the bottom of the page and click the "
    "'More' link. Then tell me the title of the first story on that second page."
)

# browser-use can't install its own Chrome here, so reuse Playwright's.
CHROME = next(Path.home().glob(
    "Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
))


async def main() -> None:
    if os.getenv("ENV") == "Prod":
        # gpt-6-luna rejects temperature/frequency_penalty. It's newer than browser-use's
        # built-in reasoning-model list, so add it there and browser-use drops both.
        llm = ChatOpenAI(model="gpt-6-luna", api_key=os.getenv("OPENAI_API_KEY"), reasoning_models=["gpt-6-luna"])
    else:
        # Ollama's default context window is too small for browser-use's page text.
        llm = ChatOllama(model="mistral:latest", ollama_options={"num_ctx": 16384})
    # Visible window, a side panel narrating each action, an orange flash on every element it
    # clicks, and a pause between actions so you can follow along.
    profile = BrowserProfile(
        executable_path=str(CHROME),
        headless=False,
        demo_mode=True,
        highlight_elements=True,
        interaction_highlight_duration=2.0,
        wait_between_actions=1.0,
    )
    agent = Agent(task=TASK, llm=llm, use_vision=False, browser_profile=profile)

    start = time.perf_counter()
    history = await agent.run(max_steps=15)
    print(f"\nanswer: {history.final_result()}")
    print(f"finished: {history.is_done()}  steps: {history.number_of_steps()}  time: {time.perf_counter() - start:.0f}s")


if __name__ == "__main__":
    asyncio.run(main())
