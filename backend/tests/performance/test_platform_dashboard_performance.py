"""PERF — Platform dashboard."""

from __future__ import annotations

import pytest

from tests.performance.helpers import measure_latencies, performance_enabled

pytestmark = pytest.mark.skipif(not performance_enabled(), reason="ELFIS_PERFORMANCE_TESTS_ENABLED=false")


@pytest.mark.parametrize("period", ["24h", "7d", "30d"])
def test_perf_004_platform_dashboard(api, period):
    api.login_user("platform_admin")

    def call():
        r = api.client.get(f"/api/platform/dashboard?period={period}", headers=api._headers())
        assert r.status_code == 200
        return r

    stats = measure_latencies(call, rounds=6, warmup=1)
    assert stats["errors"] == 0
    assert stats["p95_ms"] is not None
    assert stats["p95_ms"] < 8000
    body = stats["last"].json()
    assert "organizations_total" in body or "organizations" in str(body).lower()
