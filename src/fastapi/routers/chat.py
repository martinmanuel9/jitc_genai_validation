from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.llm_service import LLMService

from sqlalchemy.orm import Session
from services.database import SessionLocal
from services.rag_service import ChatHistory

router = APIRouter()
llm_service = LLMService()


class ChatRequest(BaseModel):
    query: str


class ComplianceRequest(BaseModel):
    data_sample: str
    standards: list[str]


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Endpoint for user to send a chat query.
    """
    try:
        # 1) Get response from LLM
        response = llm_service.query_gpt4(request.query)
        
        # 2) Save the request/response pair in the database
        chat_record = ChatHistory(
            user_query=request.query,
            response=response
        )
        db.add(chat_record)
        db.commit()
        db.refresh(chat_record)

        # 3) Return the LLM response
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/chat-history")
def get_chat_history(db: Session = Depends(get_db)):
    """
    Retrieve all past chats for debugging/demo.
    """
    records = db.query(ChatHistory).all()
    # For a production use case, consider pagination or filtering.
    return [
        {
            "id": record.id,
            "user_query": record.user_query,   # <-- user’s prompt
            "response": record.response,       # <-- LLM’s response
            "timestamp": record.timestamp
        }
        for record in records
    ]


@router.post("/compliance")
async def compliance(request: ComplianceRequest, db: Session = Depends(get_db)):
    """
    Endpoint for compliance check. 
    (Optional) store data or decisions in DB if desired.
    """
    try:
        is_compliant = llm_service.compliance_check(
            request.data_sample, 
            request.standards
        )
        # For compliance, you might or might not store in DB. 
        # If you do:
        # compliance_record = ComplianceHistory(
        #    data_sample=request.data_sample,
        #    standards="; ".join(request.standards),
        #    is_compliant=is_compliant
        # )
        # db.add(compliance_record)
        # db.commit()

        return {"compliant": is_compliant}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
