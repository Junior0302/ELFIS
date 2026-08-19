"""PERF — latence API locale (SQLite / mocks)."""

from __future__ import annotations

import pytest

from tests.performance.helpers import measure_latencies, performance_enabled


pytestmark = pytest.mark.skipif(not performance_enabled(), reason="ELFIS_PERFORMANCE_TESTS_ENABLED=false")


def test_perf_001_health_baseline(api):
    def call():
        r = api.client.get("/api/health/live")
        assert r.status_code == 200
        return r

    stats = measure_latencies(call, rounds=15, warmup=2)
    assert stats["errors"] == 0
    assert stats["p95_ms"] is not None
    # Objectif indicatif local ; SQLite peut varier.
    assert stats["p95_ms"] < 2000


def test_perf_002_document_list_paginated(api):
    api.login_user("org_admin")

    def call():
        r = api.client.get(
            "/api/vault/documents?page=1&page_size=20",
            headers=api._headers(),
        )
        assert r.status_code in (200, 403)
        return r

    stats = measure_latencies(call, rounds=10, warmup=1)
    assert stats["errors"] == 0
    assert stats["p95_ms"] is not None
    assert stats["p95_ms"] < 3000
    if stats["last"] is not None and stats["last"].status_code == 200:
        body = stats["last"].json()
        blob = str(body)
        assert len(blob) < 2_000_000


def test_perf_005_bounded_responses(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/jobs?page=1&page_size=50", headers=api._headers())
    assert r.status_code == 200
    assert len(r.content) < 5_000_000
