import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL configuration. Using SQLite database file "news.db" in the root directory.
SQLALCHEMY_DATABASE_URL = "sqlite:///./news.db"

# Create the SQLAlchemy engine. 
# check_same_thread: False is needed only for SQLite to allow multiple threads to access it.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a SessionLocal class. Each instance of SessionLocal will be a database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for the database models to inherit from
Base = declarative_base()

# Dependency generator to get a database session for each request, and close it when done.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
