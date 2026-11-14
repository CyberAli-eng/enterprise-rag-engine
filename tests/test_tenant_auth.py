"""API keys bound to tenants via API_KEY_TENANTS may only use their own tenants."""
import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import routes_ingest, routes_query
from app.config import get_settings
from app.core import security
from app.core.security import authorize_tenant
from app.main import app
from app.models.schemas import QueryResponse

BINDINGS = {"acme-key": ["acme"], "multi-key": ["acme", "globex"], "admin-key": ["*"]}


@pytest.fixture(autouse=True)
def bound_keys(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # ignore a developer's local .env
    monkeypatch.setenv("API_KEYS", "acme-key,multi-key,admin-key,legacy-key")
    monkeypatch.setenv("API_KEY_TENANTS", json.dumps(BINDINGS))
    monkeypatch.delenv("STRICT_TENANT_BINDING", raising=False)
    get_settings.cache_clear()
    security._request_log.clear()
    yield
    get_settings.cache_clear()


def _status(api_key, requested):
    with pytest.raises(HTTPException) as exc:
        authorize_tenant(api_key, requested)
    return exc.value.status_code


# --- authorize_tenant -------------------------------------------------------

def test_bound_key_may_use_its_own_tenant():
    assert authorize_tenant("acme-key", "acme") == "acme"


def test_bound_key_is_forbidden_from_other_tenants():
    assert _status("acme-key", "globex") == 403
    assert _status("acme-key", "default") == 403


def test_single_tenant_key_does_not_need_tenant_id():
    assert authorize_tenant("acme-key", None) == "acme"


def test_multi_tenant_key_must_choose_a_tenant():
    assert _status("multi-key", None) == 400
    assert authorize_tenant("multi-key", "globex") == "globex"
    assert _status("multi-key", "initech") == 403


def test_wildcard_key_may_use_any_tenant():
    assert authorize_tenant("admin-key", "initech") == "initech"
    assert authorize_tenant("admin-key", None) == "default"


def test_unbound_key_keeps_legacy_behaviour_by_default():
    assert authorize_tenant("legacy-key", "globex") == "globex"
    assert authorize_tenant("legacy-key", None) == "default"


def test_strict_mode_rejects_unbound_keys(monkeypatch):
    monkeypatch.setenv("STRICT_TENANT_BINDING", "true")
    get_settings.cache_clear()
    assert _status("legacy-key", "globex") == 403
    assert authorize_tenant("acme-key", None) == "acme"  # bound keys still work


def test_without_api_keys_local_dev_is_unrestricted(monkeypatch):
    monkeypatch.setenv("API_KEYS", "")
    get_settings.cache_clear()
    assert authorize_tenant("anonymous", "globex") == "globex"


# --- through the HTTP routes --------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    calls = {}

    def fake_answer(question, tenant_id=None):
        calls["query"] = tenant_id
        return QueryResponse(answer="ok", sources=[])

    def fake_add(chunks, tenant_id=None):
        calls["ingest"] = tenant_id
        return len(chunks)

    monkeypatch.setattr(routes_query, "answer_question", fake_answer)
    monkeypatch.setattr(routes_ingest, "add_documents", fake_add)
    return TestClient(app), calls


def test_query_for_another_tenant_is_forbidden_before_retrieval(client):
    http, calls = client
    resp = http.post("/query", json={"question": "Pricing?", "tenant_id": "globex"},
                     headers={"X-API-Key": "acme-key"})
    assert resp.status_code == 403
    assert "query" not in calls  # nothing was searched


def test_query_without_tenant_uses_the_keys_tenant(client):
    http, calls = client
    resp = http.post("/query", json={"question": "Leave days?"}, headers={"X-API-Key": "acme-key"})
    assert resp.status_code == 200
    assert calls["query"] == "acme"


def test_ingest_into_another_tenant_is_forbidden(client):
    http, calls = client
    resp = http.post("/ingest", files={"files": ("a.md", b"hello", "text/markdown")},
                     data={"tenant_id": "globex"}, headers={"X-API-Key": "acme-key"})
    assert resp.status_code == 403
    assert "ingest" not in calls


def test_ingest_without_tenant_uses_the_keys_tenant(client):
    http, calls = client
    resp = http.post("/ingest", files={"files": ("a.md", b"hello", "text/markdown")},
                     headers={"X-API-Key": "acme-key"})
    assert resp.status_code == 200
    assert calls["ingest"] == "acme"
    assert resp.json()["tenant_id"] == "acme"
