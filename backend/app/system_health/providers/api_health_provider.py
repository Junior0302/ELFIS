"""Provider réel — API / processus FastAPI (pas d'auto-HTTP)."""

from __future__ import annotations

import logging
import time
from typing import Callable

from app.config import settings
from app.observability.metrics import metrics_registry
from app.security.security_config import environment_name
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow

logger = logging.getLogger(__name__)

# Horodatage processus System Health (complète metrics_registry.started_at)
PROCESS_STARTED_AT = time.time()


def _default_route_count() -> int | None:
    try:
        from app.main import app

        return len(app.routes)
    except Exception as exc:
        logger.warning("system_health_api_route_count_failed", extra={"error": type(exc).__name__})
        return None


def _app_version() -> str:
    ver = getattr(settings, "app_version", None)
    if ver:
        return str(ver)
    try:
        from app.main import app

        return str(getattr(app, "version", None) or "0.8.9")
    except Exception:
        return "0.8.9"


class ApiHealthProvider(HealthProvider):
    service_id = "api"
    service_name = "API FastAPI"
    category = HealthCategory.PLATFORM.value

    def __init__(
        self,
        *,
        route_count_fn: Callable[[], int | None] | None = None,
        started_at: float | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._route_count_fn = route_count_fn or _default_route_count
        self._started_at = started_at if started_at is not None else metrics_registry.started_at
        self._timeout = timeout_seconds

    def check_health(self) -> HealthCheckResult:
        try:
            return run_with_timeout(self._check, timeout_seconds=self._timeout, label=self.service_id)
        except Exception as exc:
            logger.warning("system_health_api_failed", extra={"error": type(exc).__name__})
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.UNHEALTHY,
                summary="Contrôle API en échec",
                latency_ms=None,
                checked_at=utcnow(),
                version=None,
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="api_check_failed",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        t0 = time.perf_counter()
        version = _app_version()
        env = environment_name()
        uptime = max(0.0, time.time() - float(self._started_at or PROCESS_STARTED_AT))
        route_count = self._route_count_fn()
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        status = HealthStatus.HEALTHY
        summary = "API processus opérationnelle"
        error_code = None
        error_message = None

        if route_count is None:
            status = HealthStatus.DEGRADED
            summary = "API OK — compteur de routes indisponible"
            error_code = "route_count_unavailable"
            error_message = "Impossible de lire app.routes"
        elif route_count <= 0:
            status = HealthStatus.DEGRADED
            summary = "API OK — aucune route enregistrée"
            error_code = "no_routes"

        metrics = [
            metric("uptime_seconds", "Uptime", round(uptime, 1), unit="s"),
            metric("route_count", "Routes FastAPI", route_count if route_count is not None else 0, unit="routes"),
            metric("environment", "Environnement", env),
        ]

        return HealthCheckResult(
            service_id=self.service_id,
            service_name=self.service_name,
            category=self.category,
            status=status,
            summary=summary,
            latency_ms=latency_ms,
            checked_at=utcnow(),
            version=version,
            metrics=metrics,
            metadata={
                "provider_mode": "real",
                "simulated": False,
                "environment": env,
                "uptime_seconds": round(uptime, 1),
                "route_count": route_count,
            },
            error_code=error_code,
            error_message=error_message,
        )
