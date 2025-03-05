import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.database import SessionLocal, ComplianceAgent, DebateSession, ChatHistory
from services.rag_service import RAGService
from services.llm_service import LLMService
from services.agent_service import AgentService
from services.rag_agent_service import RAGAgentService
from typing import Optional, List

router = APIRouter()  

rag_service = RAGService()
llm_service = LLMService()
agent_service = AgentService()
rag_agent_service = RAGAgentService()

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

class CreateAgentRequest(BaseModel):
    name: str
    model_name: str
    system_prompt: str
    user_prompt_template: str

class ComplianceCheckRequest(BaseModel):
    data_sample: str
    agent_ids: list[int]

class DebateRequest(BaseModel):
    session_id: str
    data_sample: str
    
class CreateSessionDebateRequest(BaseModel):
    session_id: str | None = None
    agent_ids: list[int]
    data_sample: str

class DebateSequenceRequest(BaseModel):
    session_id: Optional[str] = None
    agent_ids: List[int]  # in the exact run order
    data_sample: str
    
class RAGCheckRequest(BaseModel):
    query_text: str
    collection_name: str
    agent_ids: list[int]

class RAGDebateSequenceRequest(BaseModel):
    session_id: Optional[str] = None
    agent_ids: List[int]
    query_text: str
    collection_name: str
    
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
    

@router.post("/create-agent")
async def create_agent(request: CreateAgentRequest, db: Session = Depends(get_db)):
    """Create a new compliance agent."""
    try:
        new_agent = ComplianceAgent(
            name=request.name,
            model_name=request.model_name,
            system_prompt=request.system_prompt,
            user_prompt_template=request.user_prompt_template
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        return {"message": "Agent created successfully!", "agent_id": new_agent.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-agents")
async def get_agents(db: Session = Depends(get_db)):
    """Fetch all available compliance agents."""
    agents = db.query(ComplianceAgent).all()
    return {"agents": [{"id": agent.id, "name": agent.name, "model_name": agent.model_name} for agent in agents]}


@router.post("/compliance-check")
async def compliance_check(request: ComplianceCheckRequest, db: Session = Depends(get_db)):
    """
    Runs compliance checks, and if not all compliant,
    automatically triggers a debate with a new session_id.
    """
    try:
        result = agent_service.run_compliance_check(
            data_sample=request.data_sample,
            agent_ids=request.agent_ids,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-session-and-debate")
async def create_session_and_debate(request: CreateSessionDebateRequest, db: Session = Depends(get_db)):
    """
    Example: If you want a fresh session_id (or pass one in),
    and pick some agents for debate, but skip compliance checks.
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())

        # Add the agents to the DB for that session
        for idx, agent_id in enumerate(request.agent_ids):
            db.add(DebateSession(session_id=session_id, compliance_agent_id=agent_id, debate_order=idx+1))
        db.commit()

        # Then run debate
        debate_results = agent_service.run_debate(session_id, request.data_sample)
        return {"session_id": session_id, "debate_results": debate_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/debate-sequence")
async def debate_sequence(request: DebateSequenceRequest, db: Session = Depends(get_db)):
    """
    Allows a custom, ordered multi-agent debate pipeline.
    1) Optionally pass an existing session_id; if none is given, a new one is created.
    2) agent_ids is a list in the EXACT order they should run.
    3) The final result is a chain of each agent's response.
    """
    try:
        # Let the agent_service handle the logic
        session_id, debate_chain = agent_service.run_debate_sequence(
            db=db,
            session_id=request.session_id,
            agent_ids=request.agent_ids,
            data_sample=request.data_sample
        )
        return {
            "session_id": session_id,
            "debate_chain": debate_chain
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/rag-check")
async def rag_check(request: RAGCheckRequest, db: Session = Depends(get_db)):
    """
    Runs parallel RAG checks using the selected agents,
    returning 'Yes'/'No' compliance and triggers a debate if needed.
    """
    try:
        result = rag_agent_service.run_rag_check(
            query_text=request.query_text,
            collection_name=request.collection_name,
            agent_ids=request.agent_ids,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/rag-debate-sequence")
async def rag_debate_sequence(request: RAGDebateSequenceRequest, db: Session = Depends(get_db)):
    """
    Creates a new or reuses an existing session_id, 
    then runs the agents in order, each performing a RAG retrieval. 
    They see the previous context (the chain so far) and respond. 
    """
    try:
        session_id, chain = rag_agent_service.run_rag_debate_sequence(
            db=db,
            session_id=request.session_id,
            agent_ids=request.agent_ids,
            query_text=request.query_text,
            collection_name=request.collection_name
        )
        return {
            "session_id": session_id,
            "debate_chain": chain
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))