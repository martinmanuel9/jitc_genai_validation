from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.database import SessionLocal, ChatHistory
from services.rag_service import RAGService
from services.llm_service import LLMService

router = APIRouter()  

rag_service = RAGService()
llm_service = LLMService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RAGQueryRequest(BaseModel):
    query: str
    collection_name: str

class ChatRequest(BaseModel):
    query: str

# /chat Endpoint
@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        response = llm_service.query_gpt4(request.query)
        db.add(ChatHistory(user_query=request.query, response=response))
        db.commit()
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat-rag")
async def chat_rag(request: RAGQueryRequest, db: Session = Depends(get_db)):
    """
    This endpoint calls GPT-4 with retrieval (RAG) using the selected collection.
    It also stores the chat interaction in the database.
    """
    try:
        user_prompt = request.query
        collection_name = request.collection_name

        # Pass the db session to rag_service.query()
        response = rag_service.query(user_prompt, collection_name, db)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"500: RAG query failed: {str(e)}")


@router.get("/chat-history")
def get_chat_history(db: Session = Depends(get_db)):
    records = db.query(ChatHistory).all()
    return [
        {
            "id": record.id,
            "user_query": record.user_query,
            "response": record.response,
            "timestamp": record.timestamp
        }
        for record in records
    ]
