"""
The RAG pipeline itself: retrieve relevant chunks, ground the LLM's answer
in them, and return the answer alongside the sources that were used — so
callers (and end users) can verify claims rather than trust a black box.
"""
import logging
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.models.schemas import QueryResponse, SourceChunk
from app.services.llm import get_llm
from app.services.vector_store import similarity_search

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an enterprise knowledge assistant. Answer the \
user's question using ONLY the provided context. If the context does not \
contain the answer, say you don't have enough information — never invent \
facts. Be concise and cite which source(s) you drew from by their number, \
e.g. [1], [2]."""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


def _format_context(chunks) -> str:
    parts = []
    for i, doc in enumerate(chunks, start=1):
        source = doc.metadata.get("source", "unknown")
        parts.append(f"[{i}] (source: {source})\n{doc.page_content}")
    return "\n\n".join(parts)


def answer_question(question: str, tenant_id: Optional[str] = None) -> QueryResponse:
    settings = get_settings()
    chunks = similarity_search(question, k=settings.retrieval_k, tenant_id=tenant_id)

    if not chunks:
        return QueryResponse(
            answer="I don't have any indexed documents to answer this from yet.",
            sources=[],
        )

    context = _format_context(chunks)
    llm = get_llm()
    chain = _PROMPT | llm

    try:
        result = chain.invoke({"context": context, "question": question})
        answer_text = result.content if hasattr(result, "content") else str(result)
    except Exception:
        logger.exception("LLM call failed while answering question")
        raise

    sources = [
        SourceChunk(
            source=doc.metadata.get("source", "unknown"),
            snippet=doc.page_content[:280],
        )
        for doc in chunks
    ]
    return QueryResponse(answer=answer_text, sources=sources)
