from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    tenant_id: Optional[str] = Field(default=None, description="Scopes retrieval to a tenant's documents")


class SourceChunk(BaseModel):
    source: str
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


class IngestResponse(BaseModel):
    documents_ingested: int
    chunks_created: int
    tenant_id: str


class HealthResponse(BaseModel):
    status: str
    environment: str
    vector_store: str
    llm_provider: str
