"""Tests ApiHealthProvider réel."""

from __future__ import annotations

import time

from app.system_health.health_types import HealthStatus
from app.system_health.providers.api_health_provider import ApiHealthProvider


def test_api_healthy_with_routes_and_uptime():
    started = time.time() - 42.5
    provider = ApiHealthProvider(
        route_count_fn=lambda: 254,
        started_at=started,
        timeout_seconds=2.0,
    )
    result = provider.check_health()
    assert result.status == HealthStatus.HEALTHY
    assert result.service_id == "api"
    keys = {m.key: m.value for m in result.metrics}
    assert keys["route_count"] == 254
    assert keys["uptime_seconds"] >= 40
    assert result.metadata.get("provider_mode") == "real"
    assert result.metadata.get("simulated") is False
    assert result.version


def test_api_degraded_when_route_count_missing():
    provider = ApiHealthProvider(route_count_fn=lambda: None, started_at=time.time())
    result = provider.check_health()
    assert result.status == HealthStatus.DEGRADED
    assert result.error_code == "route_count_unavailable"
