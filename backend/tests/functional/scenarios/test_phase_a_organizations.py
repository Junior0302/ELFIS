"""Phase A — Organisations (ORG-001 … ORG-004)."""

from __future__ import annotations

from tests.functional.helpers.phase_a import assert_safe_error_body


def test_org_001_access_authorized_org(api):
    api.login_user("org_admin")
    r = api.client.get("/api/vault/documents", headers=api._headers())
    assert r.status_code in (200, 402)
    if r.status_code == 200:
        assert isinstance(r.json(), dict)


def test_org_002_non_member_org_refused(api, functional_db):
    api.login_user("org_admin")
    foreign = functional_db["seed"]["organizations"]["ORG_SECOND_TENANT"]["id"]
    api.org_id = foreign
    r = api.client.get("/api/vault/documents", headers=api._headers())
    assert r.status_code in (403, 401)
    assert_safe_error_body(r.json())


def test_org_003_inexistent_organization(api):
    api.login_user("org_admin")
    api.org_id = 9_999_999
    r = api.client.get("/api/vault/documents", headers=api._headers())
    assert r.status_code in (403, 401, 404)
    assert_safe_error_body(r.json())


def test_org_003b_malformed_organization_header(api):
    api.login_user("org_admin")
    headers = api._headers()
    headers["X-Organization-Id"] = "not-an-int"
    r = api.client.get("/api/vault/documents", headers=headers)
    assert r.status_code in (400, 403, 422)


def test_org_004_client_org_id_not_sufficient(api, functional_db):
    """Appartenance réelle requise — header seul ne suffit pas."""
    api.login_user("other_tenant")
    active = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    api.org_id = active
    r = api.client.get("/api/vault/documents", headers=api._headers())
    assert r.status_code in (403, 401)
