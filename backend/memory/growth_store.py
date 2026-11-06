import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from long_memory.init_db import engine
from long_memory.schema import Goals, Journal_Entries


def log_goal(goal: str, target_date: str | None = None) -> dict:
    with Session(engine) as session:
        entry = Goals(id=uuid.uuid4().hex[:8], text=goal, target_date=target_date)
        session.add(entry)
        session.commit()
        return {"id": entry.id, "text": entry.text, "target_date": entry.target_date, "created_at": entry.created_at.isoformat()}


def log_progress(note: str) -> dict:
    with Session(engine) as session:
        entry = Journal_Entries(id=uuid.uuid4().hex[:8], note=note)
        session.add(entry)
        session.commit()
        return {"id": entry.id, "note": entry.note, "created_at": entry.created_at.isoformat()}


def list_goals() -> list[dict]:
    with Session(engine) as session:
        goals = session.scalars(select(Goals).order_by(Goals.created_at))
        return [{"id": g.id, "text": g.text, "target_date": g.target_date, "created_at": g.created_at.isoformat()} for g in goals]
