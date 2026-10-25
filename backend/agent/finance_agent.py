from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from tools.finance import log_expense, get_budget_summary, get_quote, summarize_market_news
from prompts.finance_prompt import FINANCE_PROMPT
from prompts.langfuse_client import get_prompt

def make_finance_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434",
            temperature=0.1
        ),
        tools=[log_expense, get_budget_summary, get_quote, summarize_market_news],
        system_prompt=get_prompt(name="finance_prompt") or FINANCE_PROMPT,
    )
