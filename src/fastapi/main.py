from fastapi import FastAPI, APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.database import SessionLocal
from services.llm_service import LLMService
from services.rag_service import RAGService, ChatHistory

# Initialize FastAPI & services
app = FastAPI()
router = APIRouter()
rag_service = RAGService()
llm_service = LLMService()

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Models
class RAGQueryRequest(BaseModel):
    query: str
    collection_name: str

class ChatRequest(BaseModel):
    query: str

class ComplianceRequest(BaseModel):
    data_sample: str
    standards: list[str]

# ---- Chat Endpoints ----
@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Calls GPT-4 with NO retrieval."""
    try:
        response = llm_service.query_gpt4(request.query)
        db.add(ChatHistory(user_query=request.query, response=response))
        db.commit()
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat-rag")
def chat_with_rag(request: RAGQueryRequest):
    """Calls GPT-4 WITH ChromaDB retrieval."""
    try:
        response = rag_service.query(request.query, request.collection_name)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat-history")
def get_chat_history(db: Session = Depends(get_db)):
    """Retrieves past chat history."""
    records = db.query(ChatHistory).all()
    return [{"id": r.id, "user_query": r.user_query, "response": r.response, "timestamp": r.timestamp} for r in records]

# ---- Compliance Endpoint ----
@router.post("/compliance")
async def compliance(request: ComplianceRequest):
    """Checks compliance using GPT-4."""
    try:
        is_compliant = llm_service.compliance_check(request.data_sample, request.standards)
        return {"compliant": is_compliant}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Welcome to the JITC Conformance Chatbot!"}

# Include router in app
app.include_router(router)



