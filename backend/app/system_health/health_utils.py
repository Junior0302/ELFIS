"""Utilitaires partagés System Health (pas de secrets, pas de stack traces)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Callable, TypeVar

from app.system_health.health_schemas import HealthMetric
from app.system_health.health_types import HealthStatus

logger = logging.getLogger(__name__)

T = TypeVar("T")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def metric(
    key: str,
    label: str,
    value: int | float | str | None,
    *,
    unit: str | None = None,
    status: str | None = None,
    description: str | None = None,
) -> HealthMetric:
    return HealthMetric(
        key=key,
        label=label,
        value=value,
        unit=unit,
        status=status,
        description=description,
        timestamp=utcnow(),
    )


def safe_error_message(exc: BaseException, *, max_len: int = 180) -> str:
    """Message d'erreur sûr pour l'API (pas de stack, pas d'URL/secret)."""
    name = type(exc).__name__
    text = str(exc) or ""
    # Scrub patterns sensibles
    lowered = text.lower()
    for needle in ("password", "secret", "api_key", "service_role", "postgresql://", "postgres://"):
        if needle in lowered:
            return f"{name}: détail masqué"
    msg = f"{name}: {text}" if text else name
    return msg[:max_len]


def run_with_timeout(fn: Callable[[], T], *, timeout_seconds: float, label: str = "health") -> T:
    """Exécute fn avec timeout. Relève TimeoutError si dépassé."""
    timeout = max(0.1, float(timeout_seconds))
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout:
            logger.warning("system_health_timeout", extra={"provider": label, "timeout_s": timeout})
            raise TimeoutError(f"timeout after {timeout}s") from None


def status_priority(*statuses: HealthStatus) -> HealthStatus:
    """Retourne le pire statut parmi une liste."""
    order = (
        HealthStatus.UNHEALTHY,
        HealthStatus.DEGRADED,
        HealthStatus.UNKNOWN,
        HealthStatus.DISABLED,
        HealthStatus.HEALTHY,
    )
    for s in order:
        if s in statuses:
            return s
    return HealthStatus.UNKNOWN
