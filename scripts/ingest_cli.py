#!/usr/bin/env python
"""
Bulk-ingest every .txt/.md file in a folder into the configured vector store,
without going through the HTTP API. Useful for seeding a demo or for
scheduled batch ingestion jobs.

Usage:
    python scripts/ingest_cli.py ./sample_docs --tenant-id acme-corp
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document  # noqa: E402

from app.services.chunking import chunk_documents  # noqa: E402
from app.services.vector_store import add_documents  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk ingest documents into the RAG vector store")
    parser.add_argument("folder", type=str, help="Folder containing .txt/.md files")
    parser.add_argument("--tenant-id", type=str, default="default")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        raise SystemExit(f"Not a directory: {folder}")

    documents = []
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        documents.append(Document(page_content=text, metadata={"source": str(path.name)}))

    if not documents:
        print("No .txt/.md files found.")
        return

    chunks = chunk_documents(documents)
    count = add_documents(chunks, tenant_id=args.tenant_id)
    print(f"Ingested {len(documents)} files -> {count} chunks (tenant={args.tenant_id})")


if __name__ == "__main__":
    main()
