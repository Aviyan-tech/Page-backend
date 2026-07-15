import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")
    views = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.datetime.utcnow)
    ai_summary = Column(Text, nullable=True)
