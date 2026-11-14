import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.security import authorize_tenant, enforce_rate_limit, verify_api_key
from app.models.schemas import IngestResponse
from app.services.chunking import chunk_documents
from app.services.vector_store import add_documents
from langchain_core.documents import Document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"], dependencies=[Depends(enforce_rate_limit)])

_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB per file — guards against abuse/oversized uploads
_ALLOWED_EXTENSIONS = {".txt", ".md"}


@router.post("", response_model=IngestResponse)
async def ingest_documents(
    files: list[UploadFile] = File(...),
    tenant_id: Optional[str] = Form(default=None),
    api_key: str = Depends(verify_api_key),
) -> IngestResponse:
    tenant_id = authorize_tenant(api_key, tenant_id)  # 400/403 before reading any file
    documents: list[Document] = []

    for f in files:
        ext = "." + f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.filename}")

        raw = await f.read()
        if len(raw) > _MAX_FILE_BYTES:
            raise HTTPException(status_code=400, detail=f"{f.filename} exceeds 5MB limit")

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail=f"{f.filename} is not valid UTF-8 text")

        documents.append(Document(page_content=text, metadata={"source": f.filename}))

    chunks = chunk_documents(documents)
    count = add_documents(chunks, tenant_id=tenant_id)

    logger.info("Ingested %d files (%d chunks) for tenant=%s", len(documents), count, tenant_id)
    return IngestResponse(documents_ingested=len(documents), chunks_created=count, tenant_id=tenant_id)
