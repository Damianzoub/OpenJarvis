import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from long_memory.init_db import engine
from long_memory.schema import Facts


def load_facts() -> list[str]:
    with Session(engine) as session:
        return list(session.scalars(select(Facts.fact).order_by(Facts.created_at)))


def save_fact(fact: str) -> None:
    with Session(engine) as session:
        if session.scalar(select(Facts).where(Facts.fact == fact)) is None:
            session.add(Facts(id=uuid.uuid4().hex[:8], fact=fact))
            session.commit()
