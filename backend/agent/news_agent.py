from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from tools.news import get_news
from prompts.news_prompt import NEWS_PROMPT

def make_news_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434"
        ),
        tools=[get_news],
        system_prompt=NEWS_PROMPT,
    )