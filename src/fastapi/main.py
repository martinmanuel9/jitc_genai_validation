# /app/src/app/main.py

from fastapi import FastAPI
from routers import chat

app = FastAPI(
    title="JITC GenAI Conformance Chatbot",
    version="0.1.0",
    description="A chatbot using GPT-4 and LLaMA with RAG, ChromaDB"
)
CHROMADB_URL = "http://localhost:8000"
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