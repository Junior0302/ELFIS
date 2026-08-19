"""Tests API /ai/chat|context|tools|history|feedback."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.routers.ai import router
from tests.ai_assistant.helpers import make_assistant_db, seed_assistant


@pytest.fixture()
def client_ctx():
    db = make_assistant_db()
    org, user = seed_assistant(db)

    app = FastAPI()
    app.include_router(router, prefix="/api")

    def _auth():
        return AuthContext(user=user, organization_id=org.id, role="owner", permissions=["*"])

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_auth_context] = _auth
    app.dependency_overrides[require_active_subscription] = _auth
    client = TestClient(app)
    yield client, db, org, user
    db.close()


def test_chat_endpoint_structured(client_ctx):
    client, *_ = client_ctx
    res = client.post("/api/ai/chat", json={"question": "Quel est l'état de ma trésorerie ?"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["structured"]["facts"]
    assert data["tools_used"]
    assert data["message_id"]
    assert data["confidence"]


def test_context_endpoint(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/ai/context", params={"question": "vue d'ensemble"})
    assert res.status_code == 200
    ctx = res.json()["context"]
    assert ctx["intent"] == "overview"
    assert len(ctx["overview"]["kpis"]) == 9


def test_tools_endpoint(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/ai/tools")
    assert res.status_code == 200
    names = {t["name"] for t in res.json()["tools"]}
    assert "get_cashflow" in names
    assert "search_transactions" in names


def test_history_and_feedback(client_ctx):
    client, *_ = client_ctx
    chat = client.post("/api/ai/chat", json={"question": "Quels clients sont en retard ?"}).json()
    message_id = chat["message_id"]

    hist = client.get("/api/ai/history")
    assert hist.status_code == 200
    assert len(hist.json()["items"]) >= 1

    fb = client.post(
        "/api/ai/feedback",
        json={"message_id": message_id, "kind": "useful", "comment": "Clair et utile"},
    )
    assert fb.status_code == 200
    assert fb.json()["feedback"]["kind"] == "useful"

    bad = client.post(
        "/api/ai/feedback",
        json={"message_id": "does-not-exist-000", "kind": "incorrect"},
    )
    assert bad.status_code == 404


def test_suggestions_endpoint(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/ai/suggestions")
    assert res.status_code == 200
    assert res.json()["agent"] == "AI Financial Assistant"
    assert len(res.json()["suggestions"]) >= 3
