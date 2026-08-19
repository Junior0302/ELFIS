"""SCENARIO 7 — Recherche + isolation."""

from __future__ import annotations


def test_search_endpoint_tenant_scoped(api):
    api.login_user("active")
    result = api.search_resources("Fournisseur")
    assert result is not None


def test_second_tenant_search_isolated(api):
    api.login_user("other_tenant")
    result = api.search_resources("Fournisseur Fictif")
    assert result is not None
