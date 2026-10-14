from langchain_ollama import ChatOllama
from langchain.agents import create_agent 
from prompts.rag_prompt import RAG_PROMPT
from tools.knowledge import search_knowledge
def make_knowledge_agent():
    return create_agent(
        ChatOllama(
            model="mistral:latest",
            base_url="http://localhost:11434"
        ),
        tools=[search_knowledge],
        system_prompt= RAG_PROMPT
    )