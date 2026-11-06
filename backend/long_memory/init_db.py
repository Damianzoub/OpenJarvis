from sqlalchemy import create_engine
from sqlalchemy.orm import Session,DeclarativeBase

from dotenv import load_dotenv
import os 

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Not Exist DATABASE_URL")

engine = create_engine(DATABASE_URL)

class Base(DeclarativeBase):
    pass

def init_db():
    from long_memory import schema
    Base.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
        session.close()
        