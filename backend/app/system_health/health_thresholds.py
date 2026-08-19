"""Seuils System Health — centralisés et documentés.

Ces valeurs pilotent le passage healthy → degraded → unhealthy
pour les providers réels (RC2.1 étape 2). Elles sont surchargables
via Settings / variables d'environnement.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class HealthThresholds:
    """Seuils de dégradation / panne pour les contrôles internes."""

    # PostgreSQL — latence SELECT 1
    postgres_latency_degraded_ms: float = 100.0
    postgres_latency_unhealthy_ms: float = 500.0
    # Fraction checked_out / (pool_size + max_overflow)
    postgres_pool_usage_degraded: float = 0.80

    # Jobs Queue
    jobs_pending_degraded: int = 50
    jobs_failed_degraded: int = 1
    jobs_oldest_pending_degraded_seconds: int = 300  # 5 min
    jobs_stalled_unhealthy: int = 1

    # Event Bus
    events_pending_degraded: int = 50
    events_failed_degraded: int = 1
    events_oldest_pending_degraded_seconds: int = 300
    events_stalled_unhealthy: int = 1

    # Timeout par provider (secondes)
    provider_timeout_seconds: float = 5.0

    # Cache mémoire court
    cache_ttl_seconds: float = 15.0


def load_thresholds() -> HealthThresholds:
    """Charge les seuils depuis Settings (fallback = constantes ci-dessus)."""
    return HealthThresholds(
        postgres_latency_degraded_ms=float(
            getattr(settings, "system_health_postgres_latency_degraded_ms", 100.0)
        ),
        postgres_latency_unhealthy_ms=float(
            getattr(settings, "system_health_postgres_latency_unhealthy_ms", 500.0)
        ),
        postgres_pool_usage_degraded=float(
            getattr(settings, "system_health_postgres_pool_usage_degraded", 0.80)
        ),
        jobs_pending_degraded=int(getattr(settings, "system_health_jobs_pending_degraded", 50)),
        jobs_failed_degraded=int(getattr(settings, "system_health_jobs_failed_degraded", 1)),
        jobs_oldest_pending_degraded_seconds=int(
            getattr(settings, "system_health_jobs_oldest_pending_degraded_seconds", 300)
        ),
        jobs_stalled_unhealthy=int(getattr(settings, "system_health_jobs_stalled_unhealthy", 1)),
        events_pending_degraded=int(getattr(settings, "system_health_events_pending_degraded", 50)),
        events_failed_degraded=int(getattr(settings, "system_health_events_failed_degraded", 1)),
        events_oldest_pending_degraded_seconds=int(
            getattr(settings, "system_health_events_oldest_pending_degraded_seconds", 300)
        ),
        events_stalled_unhealthy=int(getattr(settings, "system_health_events_stalled_unhealthy", 1)),
        provider_timeout_seconds=float(
            getattr(settings, "system_health_provider_timeout_seconds", 5.0)
        ),
        cache_ttl_seconds=float(getattr(settings, "system_health_cache_ttl_seconds", 15.0)),
    )
