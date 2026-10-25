from langchain_ollama import ChatOllama
from langchain.agents import create_agent 
from prompts.rag_prompt import RAG_PROMPT
from tools.knowledge import search_knowledge, ingest_document
from prompts.langfuse_client import get_prompt
def make_knowledge_agent():
    return create_agent(
        ChatOllama(
            model="mistral:latest",
            base_url="http://localhost:11434",
            temperature=0.1
        ),
        tools=[search_knowledge, ingest_document],
        system_prompt= get_prompt(name="rag_prompt") or RAG_PROMPT
    )