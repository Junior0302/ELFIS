"""Tests SystemHealthService."""

from __future__ import annotations

from app.system_health.health_registry import HealthProviderRegistry
from app.system_health.health_service import SystemHealthService, compute_overall_status
from app.system_health.health_types import HealthStatus
from app.system_health.mock_health_providers import FixedHealthProvider, register_mock_providers


def test_overall_unhealthy_wins():
    results = [
        FixedHealthProvider(
            service_id="a",
            service_name="A",
            category="x",
            status=HealthStatus.HEALTHY,
            summary="ok",
        ).check_health(),
        FixedHealthProvider(
            service_id="b",
            service_name="B",
            category="x",
            status=HealthStatus.UNHEALTHY,
            summary="down",
        ).check_health(),
    ]
    assert compute_overall_status(results) == HealthStatus.UNHEALTHY


def test_overall_degraded():
    results = [
        FixedHealthProvider(
            service_id="a",
            service_name="A",
            category="x",
            status=HealthStatus.HEALTHY,
            summary="ok",
        ).check_health(),
        FixedHealthProvider(
            service_id="b",
            service_name="B",
            category="x",
            status=HealthStatus.DEGRADED,
            summary="slow",
        ).check_health(),
    ]
    assert compute_overall_status(results) == HealthStatus.DEGRADED


def test_overall_all_healthy():
    results = [
        FixedHealthProvider(
            service_id="a",
            service_name="A",
            category="x",
            status=HealthStatus.HEALTHY,
            summary="ok",
        ).check_health(),
    ]
    assert compute_overall_status(results) == HealthStatus.HEALTHY


def test_summary_counts_with_mocks():
    reg = HealthProviderRegistry()
    register_mock_providers(reg)
    svc = SystemHealthService(registry=reg)
    summary = svc.get_summary()
    assert summary.healthy_count + summary.degraded_count + summary.unhealthy_count + summary.unknown_count == len(
        summary.services
    )
    assert summary.overall_status == HealthStatus.UNHEALTHY  # OCR unhealthy
    assert summary.unhealthy_count >= 1
    assert summary.degraded_count >= 1
    # Pas de secrets
    blob = summary.model_dump_json().lower()
    for forbidden in ("password", "sk_live", "service_role", "whsec_", "api_key="):
        assert forbidden not in blob


def test_alerts_and_logs_deterministic():
    reg = HealthProviderRegistry()
    register_mock_providers(reg)
    svc = SystemHealthService(registry=reg)
    alerts = svc.get_alerts()
    assert alerts.critical_count >= 1
    assert alerts.warning_count >= 1
    logs = svc.get_logs(limit=10, level="error")
    assert logs.total >= 1
    assert all(e.level == "error" for e in logs.entries)
    logs_pg = svc.get_logs(service_id="postgresql")
    assert all(e.service_id == "postgresql" for e in logs_pg.entries)
