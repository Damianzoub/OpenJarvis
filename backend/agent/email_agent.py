import os 
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from tools.email import read_emails, create_draft
from prompts.email_prompt import EMAIL_PROMPT

def make_gmail_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434"
        ),
        tools=[read_emails, create_draft],
        system_prompt=EMAIL_PROMPT,
    )
