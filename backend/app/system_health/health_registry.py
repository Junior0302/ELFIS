"""Registry des HealthProvider — isolation des pannes."""

from __future__ import annotations

from datetime import datetime, timezone

from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_types import HealthStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class HealthProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, HealthProvider] = {}

    def register(self, provider: HealthProvider) -> None:
        sid = (provider.service_id or "").strip()
        if not sid:
            raise ValueError("service_id requis")
        if sid in self._providers:
            raise ValueError(f"Provider déjà enregistré: {sid}")
        self._providers[sid] = provider

    def unregister(self, service_id: str) -> None:
        self._providers.pop(service_id, None)

    def get(self, service_id: str) -> HealthProvider | None:
        return self._providers.get(service_id)

    def list_providers(self) -> list[HealthProvider]:
        return list(self._providers.values())

    def check_all(self) -> list[HealthCheckResult]:
        results: list[HealthCheckResult] = []
        for provider in self._providers.values():
            try:
                result = provider.check_health()
                results.append(result)
            except Exception as exc:
                results.append(
                    HealthCheckResult(
                        service_id=provider.service_id,
                        service_name=provider.service_name,
                        category=provider.category,
                        status=HealthStatus.UNHEALTHY,
                        summary="Contrôle en échec (exception isolée)",
                        latency_ms=None,
                        checked_at=_utcnow(),
                        version=None,
                        metrics=[],
                        metadata={},
                        error_code="provider_exception",
                        error_message=f"{type(exc).__name__}: contrôle indisponible",
                    )
                )
        return results


_default_registry: HealthProviderRegistry | None = None


def get_default_registry() -> HealthProviderRegistry:
    """Registry singleton selon SYSTEM_HEALTH_*_PROVIDER (défaut: mock)."""
    global _default_registry
    if _default_registry is None:
        from app.system_health.provider_bootstrap import build_default_registry

        _default_registry = build_default_registry()
    return _default_registry


def reset_default_registry_for_tests() -> None:
    global _default_registry
    _default_registry = None
