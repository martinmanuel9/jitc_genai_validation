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
@router.post("/chat-gpt4")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        response = llm_service.query_gpt4(request.query)
        db.add(ChatHistory(user_query=request.query, response=response))
        db.commit()
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/chat-llama")
async def chat_llama(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        # response = llm_service.query_llama(request.query)
        response = llm_service.query_llama_via_ollama(request.query)
        db.add(ChatHistory(user_query=request.query, response=response))
        db.commit()
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post("/chat-gpt4-rag")
async def chat_rag_gpt4(request: RAGQueryRequest, db: Session = Depends(get_db)):
    """
    This endpoint calls GPT-4 with retrieval (RAG) using the selected collection.
    It also stores the chat interaction in the database.
    """
    try:
        user_prompt = request.query
        collection_name = request.collection_name

        # Pass the db session to rag_service.query() if needed for further logging.
        response = rag_service.query_gpt(user_prompt, collection_name, db)
        db.add(ChatHistory(user_query=request.query, response=response))
        db.commit()
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"500: RAG query failed: {str(e)}")

@router.post("/chat-rag-llama")
async def chat_rag_llama(request: RAGQueryRequest, db: Session = Depends(get_db)):
    """
    Calls LLaMA3 with retrieval (RAG) using the selected collection.
    """
    try:
        user_prompt = request.query
        collection_name = request.collection_name
        response = rag_service.query_llama(user_prompt, collection_name, db)
        db.add(ChatHistory(user_query=request.query, response=response))
        db.commit()
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
