# src/fastapi/main.py

from fastapi import FastAPI
from routers import chat
import requests
from services.database import engine, Base

app = FastAPI(
    title="JITC GenAI Conformance Chatbot",
    version="0.1.0",
    description="A chatbot using GPT-4 and LLaMA with RAG, ChromaDB"
)

from services.rag_service import ChatHistory

# Create the tables on startup (for development/demo use):
# For production, consider Alembic migrations instead of auto-create.
Base.metadata.create_all(bind=engine)


CHROMADB_URL = "http://chromadb:8020"

app.include_router(chat.router)

@app.get("/test-chroma")
def test_chroma():
    try:
        response = requests.get(CHROMADB_URL)
        return {"status": "success", "chroma_response": response.text}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/")
async def root():
    return {"message": "Welcome to the JITC Conformance Chatbot!"}
