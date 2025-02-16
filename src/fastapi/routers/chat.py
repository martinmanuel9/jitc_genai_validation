from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm_service import LLMService

router = APIRouter()
llm_service = LLMService()

class ChatRequest(BaseModel):
    query: str

class ComplianceRequest(BaseModel):
    data_sample: str
    standards: list[str]

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        response = llm_service.query_gpt4(request.query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compliance")
async def compliance(request: ComplianceRequest):
    try:
        is_compliant = llm_service.compliance_check(request.data_sample, request.standards)
        return {"compliant": is_compliant}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
