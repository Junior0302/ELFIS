"""Auth Firebase — validation ID token + session ELFIS, sans affaiblir les règles."""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.audit import audit_models  # noqa: F401
from app.database import Base, get_db
from app.models_saas import OrganizationMember, User
from app.routers.auth import router
from app.services.auth import ensure_rbac_catalog, upsert_firebase_user
from app.services.firebase_auth import FirebaseAuthError, verify_id_token


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine), engine


@pytest.fixture()
def auth_db():
    factory, _engine = _session_factory()
    db = factory()
    ensure_rbac_catalog(db)
    yield db
    db.close()


@pytest.fixture()
def client(auth_db):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: auth_db
    return TestClient(app)


def test_verify_id_token_missing_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "firebase_web_api_key", "")
    with pytest.raises(FirebaseAuthError, match="indisponible"):
        asyncio.run(verify_id_token("any"))


def test_verify_id_token_rejected(monkeypatch):
    from app.config import settings
    import app.services.firebase_auth as fa

    monkeypatch.setattr(settings, "firebase_web_api_key", "AIzaSyDummyPublicWebKeyForTestsOnly12")

    class _Resp:
        status_code = 400

        def json(self):
            return {"error": {"message": "INVALID_ID_TOKEN"}}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr(fa.httpx, "AsyncClient", lambda **kwargs: _Client())
    with pytest.raises(FirebaseAuthError, match="refusée"):
        asyncio.run(verify_id_token("expired-or-invalid"))


def test_firebase_session_invalid_token_401(client, monkeypatch):
    async def _boom(_token: str):
        raise FirebaseAuthError("Authentification refusée")

    monkeypatch.setattr("app.routers.auth.verify_id_token", _boom)
    res = client.post("/api/auth/firebase", json={"id_token": "not-a-valid-firebase-token"})
    assert res.status_code == 401
    assert "refusée" in res.json()["detail"]


def test_firebase_session_creates_elfis_user_and_org(client, auth_db, monkeypatch):
    async def _ok(_token: str):
        return {"uid": "fb-uid-1", "email": "new.user@test.elfis.local", "email_verified": True}

    monkeypatch.setattr("app.routers.auth.verify_id_token", _ok)
    res = client.post("/api/auth/firebase", json={"id_token": "valid-firebase-id-token"})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["user"]["email"] == "new.user@test.elfis.local"
    assert body["memberships"]
    user = auth_db.query(User).filter(User.email == "new.user@test.elfis.local").one()
    assert user.firebase_uid == "fb-uid-1"


def test_firebase_user_without_active_membership_is_403(client, auth_db, monkeypatch):
    user = User(
        first_name="Seul",
        last_name="Compte",
        email="orphan@test.elfis.local",
        password_hash="",
        firebase_uid="fb-orphan",
        status="active",
        last_login=datetime.utcnow(),
    )
    auth_db.add(user)
    auth_db.commit()

    async def _ok(_token: str):
        return {"uid": "fb-orphan", "email": "orphan@test.elfis.local", "email_verified": True}

    monkeypatch.setattr("app.routers.auth.verify_id_token", _ok)
    res = client.post("/api/auth/firebase", json={"id_token": "valid-firebase-id-token"})
    assert res.status_code == 403
    assert "organisation" in res.json()["detail"].lower()


def test_inactive_membership_does_not_issue_session(auth_db):
    roles = ensure_rbac_catalog(auth_db)
    user = upsert_firebase_user(
        auth_db,
        firebase_uid="fb-inactive",
        email="inactive.member@test.elfis.local",
        first_name="Ina",
        last_name="Ctive",
    )
    member = (
        auth_db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == user.id)
        .one()
    )
    member.status = "removed"
    auth_db.add(member)
    auth_db.commit()
    from app.services.auth import get_user_memberships

    assert get_user_memberships(auth_db, user.id) == []
    assert roles["owner"].name == "owner"


def test_me_requires_authorization(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_rejects_invalid_elfis_jwt(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401
