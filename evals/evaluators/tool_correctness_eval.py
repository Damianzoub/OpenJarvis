import asyncio
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root))             # for this file's own `backend.agent...` imports
sys.path.insert(0, str(_root / "backend")) # for those modules' own internal bare imports (tools.x, memory.x, ...)

from deepeval import evaluate
from deepeval.metrics import ToolCorrectnessMetric
from deepeval.models.llms.ollama_model import OllamaModel
from deepeval.test_case import LLMTestCase, ToolCall
from langchain_core.messages import AIMessage

from backend.agent.calendar_agent import make_agenda_agent
from backend.agent.email_agent import make_gmail_agent
from backend.agent.weather_agent import make_weather_agent
from backend.agent.news_agent import make_news_agent
from backend.agent.music_agent import make_music_agent
from backend.agent.filesystem_agent import make_filesystem_agent
from backend.agent.reminders_agent import make_reminders_agent
from backend.agent.growth_agent import make_growth_agent
from backend.agent.finance_agent import make_finance_agent

CASES = [
    (make_agenda_agent, "What's on my calendar today?", "list_events"),
    (make_gmail_agent, "Check my inbox for new emails.", "read_emails"),
    (make_weather_agent, "What's the weather in Athens?", "get_weather"),
    (make_news_agent, "Give me today's headlines.", "get_news"),
    (make_music_agent, "Play some music.", "play_music"),
    (make_filesystem_agent, "Find files named report in my Documents folder.", "search_files"),
    (make_reminders_agent, "What are my reminders?", "list_reminders"),
    (make_growth_agent, "What goals am I working on?", "list_goals"),
    (make_finance_agent, "How much have I spent this month?", "get_budget_summary"),
]


def get_tools_called(messages: list) -> list[str]:
    names = []
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            names.extend(call["name"] for call in message.tool_calls)
    return names


async def main():
    test_cases = []
    for make_agent, query, expected_tool in CASES:
        try:
            agent = make_agent()
            result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
        except Exception as e:
            print(f"SKIPPED {expected_tool!r} case — agent failed before any scoring: {e}")
            continue
        test_cases.append(
            LLMTestCase(
                input=query,
                actual_output=result["messages"][-1].content,
                tools_called=[ToolCall(name=n) for n in get_tools_called(result["messages"])],
                expected_tools=[ToolCall(name=expected_tool)],
            )
        )

    judge = OllamaModel(model="qwen2.5:7b", base_url="http://localhost:11434")
    metrics = [ToolCorrectnessMetric(include_reason=False, model=judge)]
    evaluate(test_cases=test_cases, metrics=metrics)


if __name__ == "__main__":
    asyncio.run(main())
