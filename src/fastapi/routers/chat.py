# /app/src/app/routers/chat.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm_service import LLMService

router = APIRouter()

class ChatRequest(BaseModel):
    query: str

@router.post("/chat")
async def chat(request: ChatRequest):
    llm_service = LLMService()
    try:
        response = llm_service.generate_response(request.query)
        # Save interaction to PostgreSQL
        # llm_service.save_interaction_to_db(request.query, response)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
