"""
Vector store abstraction.

`VECTOR_STORE` selects the backend:
- "chroma"   -> Local, disk-persisted, zero external dependency. Ideal for
                a free-tier demo deployment (Render/Railway) and for local
                development.
- "pinecone" -> Managed, cloud-native vector DB. What you'd actually reach
                for once document volume / concurrency justify it. Namespace
                support here doubles as a per-tenant isolation mechanism,
                which matters for "connect corporate data securely".

Both are wrapped behind the same interface (`get_vector_store`,
`add_documents`, `similarity_search`) so the rest of the app never branches
on which one is active.
"""
from functools import lru_cache
from typing import Optional

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from app.config import get_settings
from app.services.embeddings import get_embeddings


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    embeddings = get_embeddings()

    if settings.vector_store == "pinecone":
        return _get_pinecone_store(embeddings)

    return _get_chroma_store(embeddings)


def _get_chroma_store(embeddings) -> VectorStore:
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=get_settings().chroma_collection,
        embedding_function=embeddings,
        persist_directory=get_settings().chroma_persist_dir,
    )


def _get_pinecone_store(embeddings) -> VectorStore:
    from langchain_pinecone import PineconeVectorStore
    from pinecone import Pinecone, ServerlessSpec

    settings = get_settings()
    if not settings.pinecone_api_key:
        raise RuntimeError("VECTOR_STORE=pinecone requires PINECONE_API_KEY to be set")

    pc = Pinecone(api_key=settings.pinecone_api_key)
    existing = [idx["name"] for idx in pc.list_indexes()]
    if settings.pinecone_index not in existing:
        pc.create_index(
            name=settings.pinecone_index,
            dimension=384 if settings.embedding_provider == "local" else 1536,
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )

    return PineconeVectorStore(index_name=settings.pinecone_index, embedding=embeddings)


def add_documents(
    documents: list[Document],
    tenant_id: Optional[str] = None,
) -> int:
    """Embed and upsert documents. `tenant_id` is stamped into metadata so
    queries can be scoped per-customer/business-unit — this is the hook for
    multi-tenant document isolation."""
    store = get_vector_store()
    for doc in documents:
        doc.metadata = {**doc.metadata, "tenant_id": tenant_id or "default"}
    ids = store.add_documents(documents)
    return len(ids)


def similarity_search(query: str, k: int, tenant_id: Optional[str] = None) -> list[Document]:
    """Search within exactly one tenant. A missing tenant_id means the "default"
    tenant (the same rule add_documents uses), never "all tenants"."""
    store = get_vector_store()
    filter_ = {"tenant_id": tenant_id or "default"}
    return store.similarity_search(query, k=k, filter=filter_)
