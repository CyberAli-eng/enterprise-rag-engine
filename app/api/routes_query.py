import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import enforce_rate_limit
from app.models.schemas import QueryRequest, QueryResponse
from app.services.rag_pipeline import answer_question

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"], dependencies=[Depends(enforce_rate_limit)])


@router.post("", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        return answer_question(request.question, tenant_id=request.tenant_id)
    except Exception:
        logger.exception("Failed to answer question")
        raise HTTPException(status_code=502, detail="Upstream LLM/vector store request failed")
