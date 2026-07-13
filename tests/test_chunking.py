from langchain_core.documents import Document

from app.services.chunking import chunk_documents


def test_chunking_splits_long_text():
    long_text = "sentence. " * 500
    docs = [Document(page_content=long_text, metadata={"source": "test.txt"})]
    chunks = chunk_documents(docs)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.metadata["source"] == "test.txt"


def test_chunking_preserves_short_text():
    docs = [Document(page_content="A short document.", metadata={"source": "short.txt"})]
    chunks = chunk_documents(docs)
    assert len(chunks) == 1
    assert chunks[0].page_content == "A short document."
