"""Provider réel — PostgreSQL via SQLAlchemy (SELECT 1 + métriques pool)."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_thresholds import HealthThresholds, load_thresholds
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow

logger = logging.getLogger(__name__)


def _default_session_factory() -> Session:
    from app.database import SessionLocal

    return SessionLocal()


def _default_engine():
    from app.database import engine

    return engine


class PostgresqlHealthProvider(HealthProvider):
    service_id = "postgresql"
    service_name = "PostgreSQL"
    category = HealthCategory.DATA.value

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
        engine_factory: Callable[[], Any] | None = None,
        thresholds: HealthThresholds | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._session_factory = session_factory or _default_session_factory
        self._engine_factory = engine_factory or _default_engine
        self._thresholds = thresholds or load_thresholds()
        self._timeout = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else self._thresholds.provider_timeout_seconds
        )

    def check_health(self) -> HealthCheckResult:
        try:
            return run_with_timeout(self._check, timeout_seconds=self._timeout, label=self.service_id)
        except Exception as exc:
            logger.warning("system_health_postgresql_failed", extra={"error": type(exc).__name__})
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.UNHEALTHY,
                summary="Base de données inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version=None,
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="db_unreachable",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        db = self._session_factory()
        try:
            t0 = time.perf_counter()
            db.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            dialect = getattr(db.bind, "dialect", None)
            dialect_name = getattr(dialect, "name", "unknown") if dialect else "unknown"

            version: str | None = None
            active_connections: int | None = None
            max_connections: int | None = None
            partial = False

            if dialect_name == "postgresql":
                try:
                    version = str(db.execute(text("SHOW server_version")).scalar() or "")
                except Exception:
                    partial = True
                    version = None
                try:
                    active_connections = int(
                        db.execute(text("SELECT count(*)::int FROM pg_stat_activity")).scalar() or 0
                    )
                except Exception:
                    partial = True
                try:
                    max_connections = int(db.execute(text("SHOW max_connections")).scalar() or 0)
                except Exception:
                    partial = True
            else:
                version = dialect_name

            pool_size = int(getattr(settings, "database_pool_size", 5) or 5)
            max_overflow = int(getattr(settings, "database_max_overflow", 10) or 10)
            checked_out: int | None = None
            overflow: int | None = None
            available: int | None = None

            try:
                engine = self._engine_factory()
                pool = getattr(engine, "pool", None)
                if pool is not None:
                    if hasattr(pool, "size"):
                        try:
                            pool_size = int(pool.size())
                        except Exception:
                            pass
                    if hasattr(pool, "checkedout"):
                        checked_out = int(pool.checkedout())
                    if hasattr(pool, "overflow"):
                        overflow = int(pool.overflow())
                    if hasattr(pool, "checkedin"):
                        available = int(pool.checkedin())
            except Exception:
                partial = True

            thr = self._thresholds
            status = HealthStatus.HEALTHY
            summary = "Base accessible — pool stable"
            error_code = None
            error_message = None

            if latency_ms >= thr.postgres_latency_unhealthy_ms:
                status = HealthStatus.UNHEALTHY
                summary = f"Latence DB critique ({latency_ms} ms)"
                error_code = "db_latency_critical"
            elif latency_ms >= thr.postgres_latency_degraded_ms:
                status = HealthStatus.DEGRADED
                summary = f"Latence DB élevée ({latency_ms} ms)"
                error_code = "db_latency_high"

            capacity = max(1, pool_size + max_overflow)
            if checked_out is not None:
                usage = checked_out / capacity
                if usage >= thr.postgres_pool_usage_degraded and status != HealthStatus.UNHEALTHY:
                    status = HealthStatus.DEGRADED
                    summary = f"Pool saturé ({checked_out}/{capacity})"
                    error_code = "db_pool_saturated"
                    error_message = "Utilisation du pool supérieure au seuil"

            if partial and status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED
                summary = "Base accessible — métriques partielles"
                error_code = "db_metrics_partial"

            metrics = [
                metric(
                    "active_connections",
                    "Connexions actives",
                    active_connections if active_connections is not None else checked_out,
                    unit="conn",
                ),
                metric("pool_size", "Taille du pool", pool_size, unit="conn"),
                metric("max_overflow", "Overflow max", max_overflow, unit="conn"),
                metric("checked_out", "Connexions checked out", checked_out, unit="conn"),
                metric("available", "Connexions disponibles", available, unit="conn"),
                metric("overflow", "Overflow courant", overflow, unit="conn"),
                metric(
                    "latency_ms",
                    "Latence SELECT 1",
                    latency_ms,
                    unit="ms",
                    status=status.value,
                ),
            ]
            if max_connections is not None:
                metrics.append(
                    metric("max_connections", "max_connections", max_connections, unit="conn")
                )

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
                    "dialect": dialect_name,
                    # jamais d'URL / hôte / credentials
                },
                error_code=error_code,
                error_message=error_message,
            )
        finally:
            db.close()
