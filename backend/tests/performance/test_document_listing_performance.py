"""PERF — listes documents paginées."""

from __future__ import annotations

import pytest

from tests.performance.helpers import performance_enabled

pytestmark = pytest.mark.skipif(not performance_enabled(), reason="ELFIS_PERFORMANCE_TESTS_ENABLED=false")


def test_document_listing_pages(api):
    api.login_user("org_admin")
    for page, size in ((1, 1), (1, 20), (1, 50), (99, 20)):
        r = api.client.get(
            f"/api/vault/documents?page={page}&page_size={size}",
            headers=api._headers(),
        )
        assert r.status_code in (200, 400, 403, 422)
        if r.status_code == 200:
            assert len(r.content) < 2_000_000
