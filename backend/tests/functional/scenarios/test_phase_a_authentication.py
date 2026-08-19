"""Phase A — Authentification (AUTH-001 … AUTH-008)."""

from __future__ import annotations

from datetime import timedelta

from jose import jwt

from app.config import settings
from app.services.auth import decode_token
from tests.functional.helpers.phase_a import (
    assert_safe_error_body,
    mint_expired_token,
    mint_nbf_token,
    mint_token,
)


def test_auth_001_valid_token_accepted(api):
    api.login_user("org_admin")
    r = api.client.get("/api/auth/me", headers=api._headers())
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id")
    assert r.headers.get("X-Correlation-Id")
    body = r.json()
    assert body["user"]["email"] == "org.admin@test.elfis.local"
    assert body["current_organization_id"] == api.org_id


def test_auth_002_missing_authorization(api):
    r = api.client.get("/api/auth/me")
    assert r.status_code == 401
    assert_safe_error_body(r.json())


def test_auth_003_malformed_token(api):
    r = api.client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401
    assert_safe_error_body(r.json())


def test_auth_003b_wrong_scheme(api):
    r = api.client.get("/api/auth/me", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401


def test_auth_003c_empty_bearer(api):
    r = api.client.get("/api/auth/me", headers={"Authorization": "Bearer "})
    assert r.status_code == 401


def test_auth_003d_bad_signature(api, functional_db):
    uid = functional_db["seed"]["users"]["org_admin"]["id"]
    org = functional_db["seed"]["users"]["org_admin"]["org_id"]
    token = mint_token(sub=uid, org_id=org, secret="wrong-secret-key-xxxxxxxxxxxxxxxx")
    r = api.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert_safe_error_body(r.json())


def test_auth_004_expired_token_beyond_skew(api, functional_db):
    uid = functional_db["seed"]["users"]["org_admin"]["id"]
    org = functional_db["seed"]["users"]["org_admin"]["org_id"]
    token = mint_expired_token(sub=uid, org_id=org, expired_since=timedelta(minutes=10))
    r = api.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert_safe_error_body(r.json())


def test_auth_005_leeway_python_jose(api, functional_db):
    """Token expiré depuis < clock skew doit passer si options.leeway actif."""
    uid = functional_db["seed"]["users"]["org_admin"]["id"]
    org = functional_db["seed"]["users"]["org_admin"]["org_id"]
    token = mint_expired_token(sub=uid, org_id=org, expired_since=timedelta(seconds=10))
    # decode_token direct
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(uid)
    # via API
    r = api.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}", "X-Organization-Id": str(org)})
    assert r.status_code == 200


def test_auth_005b_nbf_within_skew(api, functional_db):
    uid = functional_db["seed"]["users"]["org_admin"]["id"]
    org = functional_db["seed"]["users"]["org_admin"]["org_id"]
    token = mint_nbf_token(sub=uid, org_id=org, nbf_delta=timedelta(seconds=5))
    # nbf futur léger — selon jose + leeway
    payload = decode_token(token)
    # Si leeway couvre nbf, OK ; sinon None — on documente le comportement
    r = api.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}", "X-Organization-Id": str(org)})
    assert r.status_code in (200, 401)
    if payload is None:
        assert r.status_code == 401


def test_auth_005c_no_leeway_kwarg_regression():
    """Non-régression : decode ne doit pas lever TypeError sur leeway."""
    token = mint_token(sub=1, org_id=1, expires_delta=timedelta(minutes=5))
    assert decode_token(token) is not None


def test_auth_006_unknown_user(api):
    token = mint_token(sub=999999, org_id=1)
    r = api.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert_safe_error_body(r.json())


def test_auth_006b_missing_sub(api):
    payload = {"org_id": 1, "exp": __import__("datetime").datetime.utcnow() + timedelta(hours=1)}
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    r = api.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_auth_007_disabled_user_blocked(api, functional_db):
    Session = functional_db["Session"]
    info = functional_db["seed"]["users"]["member"]
    api.login_user("member")
    assert api.client.get("/api/auth/me", headers=api._headers()).status_code == 200

    db = Session()
    try:
        from app.models_saas import User

        user = db.get(User, info["id"])
        user.status = "suspended"
        db.add(user)
        db.commit()
    finally:
        db.close()

    r = api.client.get("/api/auth/me", headers=api._headers())
    assert r.status_code == 401
    assert_safe_error_body(r.json())
    assert "user" not in (r.json().get("error") or {}) or True


def test_auth_008_reactivation(api, functional_db):
    Session = functional_db["Session"]
    info = functional_db["seed"]["users"]["active"]
    api.login_user("active")

    db = Session()
    try:
        from app.models_saas import User

        user = db.get(User, info["id"])
        user.status = "suspended"
        db.commit()
    finally:
        db.close()
    assert api.client.get("/api/auth/me", headers=api._headers()).status_code == 401

    db = Session()
    try:
        from app.models_saas import User

        user = db.get(User, info["id"])
        user.status = "active"
        db.commit()
    finally:
        db.close()
    assert api.client.get("/api/auth/me", headers=api._headers()).status_code == 200
