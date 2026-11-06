from pipecat.flows import FlowManager,NodeConfig

from prompts.calendar_prompt import get_calendar_prompt
from prompts.email_prompt import EMAIL_PROMPT
from prompts.finance_prompt import FINANCE_PROMPT
from prompts.excel_prompt import EXCEL_PROMPT
from prompts.growth_prompt import GROWTH_PROMPT
from prompts.music_prompt import MUSIC_PROMPT
from prompts.news_prompt import NEWS_PROMPT
from prompts.pdf_prompt import PDF_PROMPT
from prompts.powerpoint_prompt import POWERPOINT_PROMPT
from prompts.rag_prompt import RAG_PROMPT
from prompts.reminders_prompt import REMINDERS_PROMPT
from agent.filesystem_agent import FILESYSTEM_PROMPT
from agent.orchestrator import GENERAL_PROMPT
from prompts.weather_prompt import WEATHER_PROMPT
from prompts.langfuse_client import get_prompt
from .tools import AGENT_TOOLS

PROMPTS = {
    "General": GENERAL_PROMPT,
    "Filesystem": FILESYSTEM_PROMPT,
    "Email": EMAIL_PROMPT,
    "Calendar": get_calendar_prompt(),
    "Weather": WEATHER_PROMPT,
    "News": NEWS_PROMPT,
    "Music": MUSIC_PROMPT,
    "Knowledge": RAG_PROMPT,
    "Reminders": REMINDERS_PROMPT,
    "Growth": GROWTH_PROMPT,
    "Finance": FINANCE_PROMPT,
    "PDF": PDF_PROMPT,
    "Excel": EXCEL_PROMPT,
    "PowerPoint": POWERPOINT_PROMPT,
}

LANGFUSE_NAMES = {
    "Email": "email_prompt",
    "Weather": "weather_prompt",
    "News": "news_prompt",
    "Music": "music_prompt",
    "Knowledge": "rag_prompt",
    "Reminders": "reminders_prompt",
    "Growth": "growth_prompt",
    "Finance": "finance_prompt",
    "PDF": "pdf_prompt",
    "Excel": "excel_prompt",
    "PowerPoint": "powerpoint_prompt",
}



def agent_node(name:str)->NodeConfig:
    return NodeConfig(
        name=name,
        role_message=get_prompt(name=LANGFUSE_NAMES.get(name, "")) or PROMPTS[name],
        task_messages=[{
            "role":"developer",
            "content":"Help the user with their request"
        }],
        functions=AGENT_TOOLS.get(name,[])
    )

async def switch_agent(flow_manager:FlowManager,agent:str):
    # first line becomes the description of what the tool does
    # the args: lins describe each input
    """Hand the conversation to the assistant that handles this request.

    Args:
        agent: One of General, Filesystem, Email, Calendar, Weather, News, Music, Knowledge, Reminders, Growth, Finance, PDF, Excel, PowerPoint.
    """
    if agent not in PROMPTS:
        return {"switched":False,"message":f"No agent called {agent}"} , None
    return {"switched":True} , agent_node(agent)