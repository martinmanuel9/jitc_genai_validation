import os
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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

def init_db():
    """
    Import models so that they are registered with Base.metadata, then create all tables.
    """
    # Import your model(s) from the rag_service module
    from services.rag_service import ChatHistory
    # Create all tables defined in your models
    Base.metadata.create_all(bind=engine)
