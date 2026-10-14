from langgraph.graph import MessagesState
from langchain_ollama import ChatOllama
from langchain.agents import create_agent

from prompts.router_prompt import _ROUTER_PROMPT


def _make_llm():
    return ChatOllama(
        model="qwen2.5:7b",
        base_url="http://localhost:11434",
    )

def make_general_agent():
    return create_agent(
        _make_llm(),
        tools=[],
        system_prompt="You are Jarvis, an AI desktop assistant. Answer the user's question helpfully and concisely. YOUR GOAL IS TO ANSWER SIMPLE FAQs and trivial questions"
    )


async def _classify(user_message: str) -> str:
    agent = create_agent(_make_llm(), tools=[], system_prompt=_ROUTER_PROMPT)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": user_message}]})
    return result["messages"][-1].content.strip().lower()

async def route(user_message: str) -> str:
    decision = await _classify(user_message)
    if "filesystem" in decision:
        return "Filesystem"
    if "email" in decision:
        return "Email"
    if "calendar" in decision:
        return "Calendar"
    if "weather" in decision:
        return "Weather"
    if "news" in decision:
        return "News"
    if "music" in decision:
        return "Music"
    if "knowledge" in decision:
        return "Knowledge"
    return "General"