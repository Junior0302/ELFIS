"""Wrapper cache TTL autour d'un HealthProvider."""

from __future__ import annotations

from app.system_health.health_cache import TtlCache
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult


class CachedHealthProvider(HealthProvider):
    """Délègue à un provider interne avec cache mémoire court."""

    def __init__(
        self,
        inner: HealthProvider,
        *,
        ttl_seconds: float = 15.0,
        cache: TtlCache[HealthCheckResult] | None = None,
    ) -> None:
        self._inner = inner
        self.service_id = inner.service_id
        self.service_name = inner.service_name
        self.category = inner.category
        self._cache = cache or TtlCache[HealthCheckResult](ttl_seconds=ttl_seconds)

    @property
    def cache(self) -> TtlCache[HealthCheckResult]:
        return self._cache

    def invalidate_cache(self) -> None:
        self._cache.clear()

    def check_health(self) -> HealthCheckResult:
        cached = self._cache.get()
        if cached is not None:
            # Copie légère pour éviter mutations
            return cached.model_copy(deep=True)
        result = self._inner.check_health()
        self._cache.set(result)
        return result.model_copy(deep=True)
