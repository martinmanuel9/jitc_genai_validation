from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from services.database import Base

class ChatHistory(Base):
    """
    Table for recording user chat requests and responses.
    """
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_query = Column(String)
    response = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
