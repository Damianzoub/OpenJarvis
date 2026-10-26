from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from prompts.langfuse_client import get_prompt
from prompts.finance_prompt import FINANCE_PROMPT
from tools.finance import log_expense, get_budget_summary, get_quote, summarize_market_news

import os
from dotenv import load_dotenv

load_dotenv()

def make_finance_agent():
    if os.getenv("ENV") == "Prod":
        api_key = os.getenv("OPENAI_API_KEY") or None
        if api_key is None:
            raise ValueError("We don't have an API KEY")
        llm = ChatOpenAI(model="gpt-6-luna",api_key=api_key,temperature=0.1)
    else:
        llm = ChatOllama(model="qwen2.5:7b",temperature=0.1)
    return create_agent(model=llm,tools=[log_expense, get_budget_summary, get_quote, summarize_market_news],system_prompt=get_prompt(name="finance_prompt") or FINANCE_PROMPT)
