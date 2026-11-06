from pipecat.flows import FlowManager

from tools import calendar, email, finance, growth, knowledge, music, news, open_app as apps, reminders, search_files as files, weather


# Filesystem
async def search_files(flow_manager: FlowManager, directory: str, pattern: str, max_depth: int = 3):
    """Search a directory for files whose names match a pattern.

    Args:
        directory: Folder to search in.
        pattern: File name pattern, for example *.pdf.
        max_depth: How many folder levels deep to search.
    """
    return await files.search_files.ainvoke({"directory": directory, "pattern": pattern, "max_depth": max_depth}), None


async def read_file(flow_manager: FlowManager, path: str, max_chars: int = 20000):
    """Read the text of a file.

    Args:
        path: Path to the file.
        max_chars: Maximum number of characters to read.
    """
    return await files.read_file.ainvoke({"path": path, "max_chars": max_chars}), None


async def open_app(flow_manager: FlowManager, app_name: str):
    """Open a macOS application by name.

    Args:
        app_name: Name of the application, for example Safari.
    """
    return await apps.open_app.ainvoke({"app_name": app_name}), None


# Email
async def read_emails(flow_manager: FlowManager, max_results: int = 5):
    """Read the most recent emails in the inbox.

    Args:
        max_results: How many emails to read.
    """
    return await email.read_emails.ainvoke({"max_results": max_results}), None


async def create_draft(flow_manager: FlowManager, to: str, subject: str, body: str):
    """Create an email draft. It is not sent.

    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email body.
    """
    return await email.create_draft.ainvoke({"to": to, "subject": subject, "body": body}), None


# Calendar
async def list_events(flow_manager: FlowManager, days: int = 7):
    """List upcoming calendar events.

    Args:
        days: How many days ahead to look.
    """
    return await calendar.list_events.ainvoke({"days": days}), None


async def create_event(flow_manager: FlowManager, title: str, start: str, end: str, repeat: str = "none"):
    """Create a calendar event.

    Args:
        title: Event title.
        start: Start time as an ISO datetime.
        end: End time as an ISO datetime.
        repeat: none, daily, weekly, monthly or yearly.
    """
    return await calendar.create_event.ainvoke({"title": title, "start": start, "end": end, "repeat": repeat}), None


# Weather
async def get_weather(flow_manager: FlowManager, location: str):
    """Get the current weather for a location.

    Args:
        location: City or place name.
    """
    return await weather.get_weather.ainvoke({"location": location}), None


# News
async def get_news(flow_manager: FlowManager, category: str = "general", count: int = 5):
    """Get the latest news headlines.

    Args:
        category: News category, for example general, technology or business.
        count: How many headlines to return.
    """
    return await news.get_news.ainvoke({"category": category, "count": count}), None


# Music
async def play_music(flow_manager: FlowManager, query: str = ""):
    """Play music, optionally searching for a song, artist or playlist.

    Args:
        query: What to play. Leave empty to resume.
    """
    return await music.play_music.ainvoke({"query": query}), None


async def pause_music(flow_manager: FlowManager):
    """Pause the music."""
    return await music.pause_music.ainvoke({}), None


async def previous_track(flow_manager: FlowManager):
    """Go back to the previous track."""
    return await music.previous_track.ainvoke({}), None


async def next_track(flow_manager: FlowManager):
    """Skip to the next track."""
    return await music.next_track.ainvoke({}), None


async def set_volume(flow_manager: FlowManager, level: int):
    """Set the music volume.

    Args:
        level: Volume from 0 to 100.
    """
    return await music.set_volume.ainvoke({"level": level}), None


async def current_track_info(flow_manager: FlowManager):
    """Say which track is playing now."""
    return await music.current_track_info.ainvoke({}), None


# Knowledge
async def search_knowledge(flow_manager: FlowManager, query: str):
    """Search the user's personal notes and documents.

    Args:
        query: What to search for.
    """
    return await knowledge.search_knowledge.ainvoke({"query": query}), None


async def ingest_document(flow_manager: FlowManager, path: str):
    """Add a file to the user's personal notes.

    Args:
        path: Path to the file to add.
    """
    return await knowledge.ingest_document.ainvoke({"path": path}), None


# Reminders
async def add_reminder(flow_manager: FlowManager, text: str, due: str | None = None):
    """Add a reminder.

    Args:
        text: What to be reminded about.
        due: Optional ISO datetime when it is due.
    """
    return await reminders.add_reminder.ainvoke({"text": text, "due": due}), None


async def list_reminders(flow_manager: FlowManager, include_done: bool = False):
    """List the user's reminders.

    Args:
        include_done: Also include completed reminders.
    """
    return await reminders.list_reminders.ainvoke({"include_done": include_done}), None


async def complete_reminder(flow_manager: FlowManager, reminder_id: str):
    """Mark a reminder as done.

    Args:
        reminder_id: Id of the reminder.
    """
    return await reminders.complete_reminder.ainvoke({"reminder_id": reminder_id}), None


# Growth
async def log_goal(flow_manager: FlowManager, goal: str, target_date: str | None = None):
    """Log a personal growth goal.

    Args:
        goal: The goal.
        target_date: Optional date to reach it by.
    """
    return await growth.log_goal.ainvoke({"goal": goal, "target_date": target_date}), None


async def log_progress(flow_manager: FlowManager, note: str):
    """Log a short journal entry about progress toward a goal.

    Args:
        note: The journal entry.
    """
    return await growth.log_progress.ainvoke({"note": note}), None


async def list_goals(flow_manager: FlowManager):
    """List the user's current growth goals."""
    return await growth.list_goals.ainvoke({}), None


# Finance
async def log_expense(flow_manager: FlowManager, amount: float, category: str, note: str = ""):
    """Log an expense.

    Args:
        amount: How much was spent.
        category: Spending category, for example food.
        note: Optional note.
    """
    return await finance.log_expense.ainvoke({"amount": amount, "category": category, "note": note}), None


async def get_budget_summary(flow_manager: FlowManager):
    """Summarise the user's spending."""
    return await finance.get_budget_summary.ainvoke({}), None


async def get_quote(flow_manager: FlowManager, symbol: str):
    """Get the current price of a stock or crypto.

    Args:
        symbol: Ticker symbol, for example AAPL.
    """
    return await finance.get_quote.ainvoke({"symbol": symbol}), None


async def summarize_market_news(flow_manager: FlowManager, topic: str):
    """Summarise recent market news about a topic.

    Args:
        topic: Company, market or theme.
    """
    return await finance.summarize_market_news.ainvoke({"topic": topic}), None


# same tools per agent as backend/agent/
AGENT_TOOLS = {
    "Filesystem": [search_files, read_file, open_app],
    "Email": [read_emails, create_draft],
    "Calendar": [list_events, create_event],
    "Weather": [get_weather],
    "News": [get_news],
    "Music": [play_music, pause_music, previous_track, next_track, set_volume, current_track_info],
    "Knowledge": [search_knowledge, ingest_document],
    "Reminders": [add_reminder, list_reminders, complete_reminder],
    "Growth": [log_goal, log_progress, list_goals],
    "Finance": [log_expense, get_budget_summary, get_quote, summarize_market_news],
}
