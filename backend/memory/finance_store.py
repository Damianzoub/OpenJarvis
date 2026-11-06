import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from long_memory.init_db import engine
from long_memory.schema import Expenses


def _to_dict(e: Expenses) -> dict:
    return {
        "id": e.id,
        "amount": float(e.amount),
        "category": e.category,
        "note": e.note,
        "created_at": e.created_at.isoformat(),
    }


def log_expense(amount: float, category: str, note: str = "") -> dict:
    with Session(engine) as session:
        entry = Expenses(id=uuid.uuid4().hex[:8], amount=amount, category=category, note=note)
        session.add(entry)
        session.commit()
        return _to_dict(entry)


def list_expenses() -> list[dict]:
    with Session(engine) as session:
        return [_to_dict(e) for e in session.scalars(select(Expenses).order_by(Expenses.created_at))]
