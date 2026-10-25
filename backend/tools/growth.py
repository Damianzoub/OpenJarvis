from langchain.tools import tool

from memory.growth_store import log_goal as _log_goal
from memory.growth_store import log_progress as _log_progress
from memory.growth_store import list_goals as _list_goals


@tool(description="Log a personal growth or self-improvement goal, with an optional target date.")
async def log_goal(goal: str, target_date: str | None = None) -> str:
    entry = _log_goal(goal, target_date)
    return f"Goal logged: {entry['text']}" + (f" (target {entry['target_date']})" if entry['target_date'] else "")


@tool(description="Log a short journal entry or reflection on progress toward a goal.")
async def log_progress(note: str) -> str:
    _log_progress(note)
    return "Noted."


@tool(description="List all the user's current growth goals.")
async def list_goals() -> str:
    goals = _list_goals()
    if not goals:
        return "No goals logged yet."
    return "\n".join(
        f"{g['text']}" + (f" (target {g['target_date']})" if g["target_date"] else "")
        for g in goals
    )
