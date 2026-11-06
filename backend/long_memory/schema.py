from .init_db import Base
from sqlalchemy import Integer,String,Column,Float,ForeignKey,ForeignKeyConstraint,Index,UniqueConstraint,DateTime,func,Numeric,Boolean

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
    