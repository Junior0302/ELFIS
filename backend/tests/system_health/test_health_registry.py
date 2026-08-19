"""Tests HealthProviderRegistry."""

from __future__ import annotations

import pytest

from app.system_health.health_registry import HealthProviderRegistry
from app.system_health.health_types import HealthStatus
from app.system_health.mock_health_providers import (
    ExplodingHealthProvider,
    FixedHealthProvider,
    build_mock_providers,
)


def test_register_and_list():
    reg = HealthProviderRegistry()
    p = FixedHealthProvider(
        service_id="api",
        service_name="API",
        category="platform",
        status=HealthStatus.HEALTHY,
        summary="ok",
    )
    reg.register(p)
    assert reg.get("api") is p
    assert len(reg.list_providers()) == 1


def test_duplicate_rejected():
    reg = HealthProviderRegistry()
    p = FixedHealthProvider(
        service_id="api",
        service_name="API",
        category="platform",
        status=HealthStatus.HEALTHY,
        summary="ok",
    )
    reg.register(p)
    with pytest.raises(ValueError, match="déjà enregistré"):
        reg.register(p)


def test_check_all_isolates_exception():
    reg = HealthProviderRegistry()
    reg.register(
        FixedHealthProvider(
            service_id="ok",
            service_name="OK",
            category="platform",
            status=HealthStatus.HEALTHY,
            summary="ok",
            latency_ms=10,
        )
    )
    reg.register(ExplodingHealthProvider())
    results = reg.check_all()
    assert len(results) == 2
    by_id = {r.service_id: r for r in results}
    assert by_id["ok"].status == HealthStatus.HEALTHY
    assert by_id["exploding"].status == HealthStatus.UNHEALTHY
    assert by_id["exploding"].error_code == "provider_exception"
    assert "boom" not in (by_id["exploding"].error_message or "").lower() or "indisponible" in (
        by_id["exploding"].error_message or ""
    )


def test_mock_providers_deterministic_count():
    providers = build_mock_providers()
    assert len(providers) == 17
    ids = [p.service_id for p in providers]
    assert len(ids) == len(set(ids))
    assert "ocr" in ids
    assert "postgresql" in ids
