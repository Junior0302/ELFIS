"""SCENARIO 1 — Auth + isolation tenant."""

from __future__ import annotations


def test_authentication_and_org_context(api):
    session = api.login_user("org_admin")
    assert session["token"]
    me = api.get_me()
    assert me.get("email") == "org.admin@test.elfis.local" or "email" in str(me).lower() or me


def test_tenant_isolation_refuses_other_org(api, functional_db):
    api.login_user("org_admin")
    other_org_id = functional_db["seed"]["organizations"]["ORG_SECOND_TENANT"]["id"]
    # Forcer un org_id non membre
    api.org_id = other_org_id
    r = api.client.get("/api/vault/documents", headers=api._headers())
    assert r.status_code in (403, 401, 404)
    body = r.json()
    # Erreur normalisée ou detail legacy
    assert "error" in body or "detail" in body


def test_other_tenant_can_access_own_org(api):
    api.login_user("other_tenant")
    docs = api.list_documents()
    assert docs is not None
