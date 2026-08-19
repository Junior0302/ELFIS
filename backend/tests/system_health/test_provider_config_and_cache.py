"""Tests config real/mock/disabled + cache + bootstrap."""

from __future__ import annotations

from types import SimpleNamespace

from app.system_health.health_cache import TtlCache
from app.system_health.health_provider_mode import resolve_provider_mode
from app.system_health.health_registry import HealthProviderRegistry
from app.system_health.health_types import HealthStatus
from app.system_health.mock_health_providers import FixedHealthProvider
from app.system_health.provider_bootstrap import register_configured_providers
from app.system_health.providers.cached_health_provider import CachedHealthProvider


def test_resolve_modes_default_mock():
    cfg = SimpleNamespace(
        system_health_use_real_providers=False,
        system_health_api_provider="mock",
        system_health_postgres_provider="mock",
        system_health_jobs_provider="mock",
        system_health_events_provider="mock",
        system_health_search_provider="mock",
        system_health_storage_provider="mock",
    )
    assert resolve_provider_mode("api", settings_obj=cfg) == "mock"
    assert resolve_provider_mode("postgresql", settings_obj=cfg) == "mock"


def test_resolve_real_and_disabled():
    cfg = SimpleNamespace(
        system_health_use_real_providers=False,
        system_health_api_provider="real",
        system_health_postgres_provider="disabled",
        system_health_jobs_provider="real",
        system_health_events_provider="mock",
        system_health_search_provider="MOCK",
    )
    assert resolve_provider_mode("api", settings_obj=cfg) == "real"
    assert resolve_provider_mode("postgresql", settings_obj=cfg) == "disabled"
    assert resolve_provider_mode("search", settings_obj=cfg) == "mock"


def test_use_real_providers_flag():
    cfg = SimpleNamespace(
        system_health_use_real_providers=True,
        system_health_api_provider="mock",
        system_health_postgres_provider="disabled",
        system_health_jobs_provider="mock",
        system_health_events_provider="mock",
        system_health_search_provider="mock",
        system_health_storage_provider="mock",
    )
    assert resolve_provider_mode("api", settings_obj=cfg) == "real"
    assert resolve_provider_mode("postgresql", settings_obj=cfg) == "disabled"


def test_invalid_mode_falls_back_to_mock():
    cfg = SimpleNamespace(
        system_health_use_real_providers=False,
        system_health_api_provider="weird",
        system_health_postgres_provider="mock",
        system_health_jobs_provider="mock",
        system_health_events_provider="mock",
        system_health_search_provider="mock",
        system_health_storage_provider="mock",
    )
    assert resolve_provider_mode("api", settings_obj=cfg) == "mock"


def test_cache_hit_and_expire():
    cache: TtlCache[str] = TtlCache(ttl_seconds=60)
    assert cache.get() is None
    cache.set("a")
    assert cache.get() == "a"
    cache.force_expire()
    assert cache.get() is None


def test_cached_provider_avoids_second_call():
    calls = {"n": 0}

    class CountingProvider(FixedHealthProvider):
        def check_health(self):
            calls["n"] += 1
            return super().check_health()

    inner = CountingProvider(
        service_id="api",
        service_name="API",
        category="platform",
        status=HealthStatus.HEALTHY,
        summary="ok",
    )
    cached = CachedHealthProvider(inner, ttl_seconds=60)
    r1 = cached.check_health()
    r2 = cached.check_health()
    assert calls["n"] == 1
    assert r1.status == r2.status == HealthStatus.HEALTHY
    cached.invalidate_cache()
    cached.check_health()
    assert calls["n"] == 2


def test_bootstrap_disabled_provider():
    cfg = SimpleNamespace(
        system_health_use_real_providers=False,
        system_health_api_provider="disabled",
        system_health_postgres_provider="mock",
        system_health_jobs_provider="mock",
        system_health_events_provider="mock",
        system_health_search_provider="mock",
        system_health_storage_provider="mock",
        system_health_cache_ttl_seconds=15,
        system_health_provider_timeout_seconds=5,
        system_health_postgres_latency_degraded_ms=100,
        system_health_postgres_latency_unhealthy_ms=500,
        system_health_postgres_pool_usage_degraded=0.8,
        system_health_jobs_pending_degraded=50,
        system_health_jobs_failed_degraded=1,
        system_health_jobs_oldest_pending_degraded_seconds=300,
        system_health_jobs_stalled_unhealthy=1,
        system_health_events_pending_degraded=50,
        system_health_events_failed_degraded=1,
        system_health_events_oldest_pending_degraded_seconds=300,
        system_health_events_stalled_unhealthy=1,
    )
    reg = HealthProviderRegistry()
    register_configured_providers(reg, settings_obj=cfg, wrap_cache=False)
    api = reg.get("api")
    assert api is not None
    result = api.check_health()
    assert result.status == HealthStatus.DISABLED
    assert len(reg.list_providers()) == 17
