import os

os.environ.setdefault("API_KEYS", "test-key-123")
os.environ.setdefault("VECTOR_STORE", "chroma")
os.environ.setdefault("CHROMA_PERSIST_DIR", "./test_chroma_db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health_is_public():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200


def test_query_requires_api_key():
    resp = client.post("/query", json={"question": "What is our refund policy?"})
    assert resp.status_code == 401


def test_query_rejects_bad_api_key():
    resp = client.post(
        "/query",
        json={"question": "What is our refund policy?"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401
