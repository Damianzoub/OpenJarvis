from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from prompts.langfuse_client import get_prompt
from prompts.pdf_prompt import PDF_PROMPT

import os
from dotenv import load_dotenv

load_dotenv()

def make_pdf_agent():
    if os.getenv("ENV") == "Prod":
        api_key = os.getenv("OPENAI_API_KEY") or None
        if api_key is None:
            raise ValueError("We don't have an API KEY")
        llm = ChatOpenAI(model="gpt-6-luna",api_key=api_key,temperature=0.1)
    else:
        llm = ChatOllama(model="mistral:latest",temperature=0.1)
    return create_agent(model=llm,tools=[],system_prompt=get_prompt(name="PDF_PROMPT") or PDF_PROMPT)
