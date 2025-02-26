import os
import time
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Pull DATABASE_URL from environment. Docker Compose sets this as:
# DATABASE_URL=postgresql://user:password@postgres_db:5432/rag_memory
DATABASE_URL = os.getenv("DATABASE_URL")

# Retry connecting to the database if it's not ready
for i in range(5):
    try:
        engine = create_engine(DATABASE_URL)
        connection = engine.connect()
        connection.close()
        break  # Connection successful!
    except OperationalError:
        print(f"Database not ready, retrying {i+1}/5...")
        time.sleep(5)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_query = Column(String)
    response = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow())

def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
