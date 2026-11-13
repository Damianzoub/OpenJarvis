from .init_db import Base
from sqlalchemy import Integer,String,Column,Float,ForeignKey,ForeignKeyConstraint,Index,UniqueConstraint,DateTime,func,Numeric,Boolean,BigInteger

class Facts(Base):
    __tablename__="facts"
    id = Column(String,primary_key=True)
    fact = Column(String,nullable=False,unique=True)
    created_at = Column(DateTime(timezone=True),nullable=False,default=func.now())

class Goals(Base):
    __tablename__ ="goals"
    id = Column(String,primary_key=True)
    text = Column(String,nullable=False)
    target_date =Column(String)
    created_at = Column(DateTime(timezone=True),nullable=False,default=func.now())


class Conversations(Base):
    __tablename__="conversations"
    id = Column(String,primary_key=True)
    title=Column(String,nullable=False)
    created_at = Column(DateTime(timezone=True),nullable=False,default=func.now())
    updated_at = Column(DateTime(timezone=True),nullable=False,default=func.now())

class Messages(Base):
    __tablename__="messages"
    id = Column(BigInteger,primary_key=True)
    conversation_id = Column(String,ForeignKey("conversations.id",ondelete="CASCADE"),nullable=False)
    role = Column(String,nullable=False)
    content = Column(String,nullable=False)
    agent =Column(String)
    created_at = Column(DateTime(timezone=True),nullable=False,default=func.now())

    __table_args__ = (
        Index("idx_messages_conversation_id","conversation_id","created_at"),
    )

class Journal_Entries(Base):
    __tablename__="journal_entries"
    id = Column(String,primary_key=True)
    note = Column(String,nullable=False)
    created_at = Column(DateTime(timezone=True),nullable=False,default=func.now())

class Reminders(Base):
    __tablename__="reminders"
    id = Column(String,primary_key=True)
    text = Column(String,nullable=False)
    due = Column(DateTime(timezone=True))
    done = Column(Boolean,nullable=False,default=False)
    notified = Column(Boolean,nullable=False,default=False)
    created_at = Column(DateTime(timezone=True),nullable=False,default=func.now())

class Expenses(Base):
    __tablename__="expenses"
    id = Column(String,primary_key=True)
    amount = Column(Numeric(12,2),nullable=False)
    category = Column(String,nullable=False)
    note = Column(String,nullable=False,default="")
    created_at = Column(DateTime(timezone=True),nullable=False,default=func.now())
    