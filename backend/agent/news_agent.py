from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from tools.news import get_news
from prompts.news_prompt import NEWS_PROMPT
from prompts.langfuse_client import get_prompt

def make_news_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434",
            temperature=0.1
        ),
        tools=[get_news],
        system_prompt=get_prompt(name="news_prompt") or NEWS_PROMPT,
    )