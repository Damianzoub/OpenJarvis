from bu_agent_sdk.agent import Agent 
from bu_agent_sdk.llm.openai.like import ChatOpenAILike
from tools.news import get_news
from prompts.news_prompt import NEWS_PROMPT

def make_news_agent():
    return Agent(
        llm=ChatOpenAILike(
            model="qwen2.5:7b",
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        ),
        tools=[get_news],
        system_prompt=NEWS_PROMPT,
    )