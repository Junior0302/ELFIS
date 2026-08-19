"""Tests SearchService + indexation."""

from __future__ import annotations

import pytest

from app.search.search_exceptions import SearchNotFoundError, SearchValidationError
from app.search.search_registry import bootstrap_indexers, default_indexer_registry
from app.search.search_schemas import SearchIndexRequest, SearchQuery
from app.search.search_security import assert_action_url, assert_query, filter_metadata
from app.search.search_service import SearchService
from app.search.search_types import IndexStatus, SearchResourceTypes
from tests.search import setup_search_db


def setup_function():
    default_indexer_registry.clear()
    bootstrap_indexers()


def test_indexers_registered():
    reg = bootstrap_indexers()
    assert reg.has(SearchResourceTypes.VAULT_DOCUMENT)
    assert reg.has(SearchResourceTypes.DOCUMENT_ANALYSIS)
    assert reg.has(SearchResourceTypes.ACCOUNTING_PROPOSAL)


def test_unknown_type_rejected():
    db, _, _ = setup_search_db()
    with pytest.raises(SearchValidationError):
        SearchService(db).index_resource(
            SearchIndexRequest(organization_id=1, resource_type="email", resource_id="x")
        )


def test_index_vault_and_search():
    db, _, _ = setup_search_db()
    svc = SearchService(db)
    r = svc.index_resource(
        SearchIndexRequest(
            organization_id=1,
            resource_type=SearchResourceTypes.VAULT_DOCUMENT,
            resource_id="vd-1",
        )
    )
    assert r.indexed
    assert r.search_document_id
    again = svc.index_resource(
        SearchIndexRequest(
            organization_id=1,
            resource_type=SearchResourceTypes.VAULT_DOCUMENT,
            resource_id="vd-1",
        )
    )
    assert again.status == IndexStatus.UNCHANGED

    res = svc.search(organization_id=1, query=SearchQuery(query="ACME"))
    assert res.total >= 1
    assert any("facture" in i.title.lower() or "acme" in i.title.lower() for i in res.items)

    by_num = svc.search(organization_id=1, query=SearchQuery(query="F2026-001"))
    assert by_num.total >= 1


def test_tenant_isolation():
    db, _, _ = setup_search_db()
    svc = SearchService(db)
    svc.index_resource(
        SearchIndexRequest(
            organization_id=1,
            resource_type=SearchResourceTypes.VAULT_DOCUMENT,
            resource_id="vd-1",
        )
    )
    res = svc.search(organization_id=2, query=SearchQuery(query="facture"))
    assert res.total == 0
    with pytest.raises(SearchNotFoundError):
        svc.index_resource(
            SearchIndexRequest(
                organization_id=2,
                resource_type=SearchResourceTypes.VAULT_DOCUMENT,
                resource_id="vd-1",
            )
        )


def test_filters_and_pagination():
    db, _, _ = setup_search_db()
    svc = SearchService(db)
    svc.index_resource(
        SearchIndexRequest(
            organization_id=1,
            resource_type=SearchResourceTypes.VAULT_DOCUMENT,
            resource_id="vd-1",
        )
    )
    res = svc.search(
        organization_id=1,
        query=SearchQuery(
            resource_types=[SearchResourceTypes.VAULT_DOCUMENT],
            amount_min=100,
            currency="EUR",
            page=1,
            page_size=10,
            sort="newest",
        ),
    )
    assert res.total >= 1
    empty = svc.search(organization_id=1, query=SearchQuery(query=""))
    assert empty.total >= 1


def test_query_and_page_limits():
    with pytest.raises(SearchValidationError):
        assert_query("x" * 500)
    with pytest.raises(SearchValidationError):
        assert_action_url("javascript:alert(1)")
    with pytest.raises(SearchValidationError):
        assert_action_url("https://evil.example/x")
    meta = filter_metadata({"signed_url": "http://x", "token": "t", "ok": "yes"})
    assert "signed_url" not in meta
    assert meta["ok"] == "yes"


def test_soft_delete():
    db, _, _ = setup_search_db()
    svc = SearchService(db)
    r = svc.index_resource(
        SearchIndexRequest(
            organization_id=1,
            resource_type=SearchResourceTypes.VAULT_DOCUMENT,
            resource_id="vd-1",
        )
    )
    svc.remove_resource(
        organization_id=1,
        resource_type=SearchResourceTypes.VAULT_DOCUMENT,
        resource_id="vd-1",
    )
    res = svc.search(organization_id=1, query=SearchQuery(query="facture"))
    assert all(i.search_document_id != r.search_document_id for i in res.items)
