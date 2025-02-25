import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import time

# Pull DATABASE_URL from environment. Docker Compose sets this as:
# DATABASE_URL=postgresql://user:password@postgres_db:5432/rag_memory
DATABASE_URL = os.getenv("DATABASE_URL")

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
