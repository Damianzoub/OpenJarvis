import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from long_memory.init_db import engine
from long_memory.schema import Reminders


def _parse_due(due: str | None) -> datetime | None:
    if not due:
        return None
    parsed = datetime.fromisoformat(due)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _to_dict(r: Reminders) -> dict:
    return {
        "id": r.id,
        "text": r.text,
        "due": r.due.isoformat() if r.due else None,
        "done": r.done,
        "notified": r.notified,
        "created_at": r.created_at.isoformat(),
    }


def add_reminder(text: str, due: str | None = None) -> dict:
    with Session(engine) as session:
        reminder = Reminders(id=uuid.uuid4().hex[:8], text=text, due=_parse_due(due))
        session.add(reminder)
        session.commit()
        return _to_dict(reminder)


def list_reminders(include_done: bool = False) -> list[dict]:
    with Session(engine) as session:
        query = select(Reminders).order_by(Reminders.created_at)
        if not include_done:
            query = query.where(Reminders.done.is_(False))
        return [_to_dict(r) for r in session.scalars(query)]


def complete_reminder(reminder_id: str) -> dict | None:
    with Session(engine) as session:
        reminder = session.get(Reminders, reminder_id)
        if reminder is None:
            return None
        reminder.done = True
        session.commit()
        return _to_dict(reminder)


def get_due_reminders() -> list[dict]:
    with Session(engine) as session:
        due = list(session.scalars(
            select(Reminders).where(
                Reminders.due.is_not(None),
                Reminders.due <= datetime.now(timezone.utc),
                Reminders.done.is_(False),
                Reminders.notified.is_(False),
            )
        ))
        for r in due:
            r.notified = True
        session.commit()
        return [_to_dict(r) for r in due]
