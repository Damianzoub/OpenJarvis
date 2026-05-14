import os 
from bu_agent_sdk import Agent
from bu_agent_sdk.llm.openai.like import ChatOpenAILike
from tools.email import read_emails, create_draft
from prompts.email_prompt import EMAIL_PROMPT

def make_gmail_agent():
    return Agent(
        llm=ChatOpenAILike(
            model="qwen2.5:7b",
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        ),
        tools=[read_emails, create_draft],
        system_prompt=EMAIL_PROMPT,
    )
