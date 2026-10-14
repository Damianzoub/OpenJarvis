from typing import Literal

from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command

from agent.calendar_agent import make_agenda_agent
from agent.email_agent import make_gmail_agent
from agent.filesystem_agent import make_filesystem_agent
from agent.music_agent import make_music_agent
from agent.news_agent import make_news_agent
from agent.orchestrator import route
from agent.weather_agent import make_weather_agent
from agent.orchestrator import make_general_agent
from agent.knowledge_agent import make_knowledge_agent

async def _classify_node(
    state: MessagesState,
) -> Command[Literal["Filesystem", "Email", "Calendar", "Weather", "News", "Music","General","Knowledge"]]:
    user_message = state["messages"][-1].content
    decision = await route(user_message)
    return Command(goto=decision)


async def agent_workflow():
    builder = StateGraph(MessagesState)
    builder.add_node("classify", _classify_node)
    builder.add_node("Filesystem", make_filesystem_agent())
    builder.add_node("Email", make_gmail_agent())
    builder.add_node("General",make_general_agent())
    builder.add_node("Calendar", make_agenda_agent())
    builder.add_node("Weather", make_weather_agent())
    builder.add_node("News", make_news_agent())
    builder.add_node("Music", make_music_agent())
    builder.add_node("Knowledge",make_knowledge_agent())

    builder.add_edge(START, "classify")
    builder.add_edge("Filesystem", END)
    builder.add_edge("Email", END)
    builder.add_edge("Calendar", END)
    builder.add_edge("Weather", END)
    builder.add_edge("News", END)
    builder.add_edge("Music", END)
    builder.add_edge("General",END)
    builder.add_edge("Knowledge",END)  
    graph = builder.compile()
    return graph
