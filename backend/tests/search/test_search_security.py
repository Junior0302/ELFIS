"""Tests sécurité Search."""

from __future__ import annotations

import pytest

from app.search.search_exceptions import SearchValidationError
from app.search.search_security import assert_action_url, assert_page_size, assert_resource_type


def test_resource_type_and_action_url():
    assert assert_resource_type("vault_document") == "vault_document"
    with pytest.raises(SearchValidationError):
        assert_resource_type("knowledge_base")
    assert assert_action_url("/documents/abc") == "/documents/abc"
    with pytest.raises(SearchValidationError):
        assert_action_url("../etc/passwd")


def test_page_size_limited(monkeypatch):
    monkeypatch.setattr("app.config.settings.elfis_search_max_page_size", 50)
    with pytest.raises(SearchValidationError):
        assert_page_size(51)
