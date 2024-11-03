# /app/src/app/main.py

from fastapi import FastAPI
from src.app.routers import chat

app = FastAPI(
    title="JITC GenAI Validation Chatbot",
    version="0.1.0",
    description="A chatbot using GPT-4 and LLaMA with RAG, Milvus, and PostgreSQL"
)

app.include_router(chat.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the JITC Validation Chatbot!"}