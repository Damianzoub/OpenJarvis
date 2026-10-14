import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from langgraph.graph import END, END, START, MessagesState, StateGraph

from backend.agent.calendar_agent import make_agenda_agent
from backend.agent.email_agent import make_gmail_agent
from backend.agent.filesystem_agent import make_filesystem_agent
from backend.agent.filesystem_agent import make_filesystem_agent
from backend.agent.music_agent import make_music_agent
from backend.agent.music_agent import make_music_agent
from backend.agent.news_agent import make_news_agent
from backend.agent.news_agent import make_news_agent
from backend.agent.orchestrator import _classify, _classify, _make_llm, route
from backend.agent.weather_agent import make_weather_agent
from backend.agent.weather_agent import make_weather_agent
from backend.graph.workflow_creation import _classify_node
from backend.agent.knowledge_agent import make_knowledge_agent
from backend.agent.orchestrator import make_general_agent


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


app = graph.compile()

print(app.get_graph().draw_mermaid())