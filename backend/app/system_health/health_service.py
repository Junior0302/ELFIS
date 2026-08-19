"""SystemHealthService — agrégation, métriques, alertes et logs simulés."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import settings
from app.security.security_config import environment_name
from app.system_health.health_registry import HealthProviderRegistry, get_default_registry
from app.system_health.health_schemas import (
    HealthCheckResult,
    HealthMetric,
    SystemAlert,
    SystemAlertsResponse,
    SystemHealthSummary,
    SystemLogEntry,
    SystemLogsResponse,
    SystemMetricsResponse,
)
from app.system_health.health_types import AlertSeverity, HealthStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_overall_status(results: list[HealthCheckResult]) -> HealthStatus:
    """Règles : unhealthy > degraded > all healthy > unknown."""
    if not results:
        return HealthStatus.UNKNOWN
    if any(r.status == HealthStatus.UNHEALTHY for r in results):
        return HealthStatus.UNHEALTHY
    if any(r.status == HealthStatus.DEGRADED for r in results):
        return HealthStatus.DEGRADED
    if all(r.status == HealthStatus.HEALTHY for r in results):
        return HealthStatus.HEALTHY
    return HealthStatus.UNKNOWN


def _count(results: list[HealthCheckResult], status: HealthStatus) -> int:
    return sum(1 for r in results if r.status == status)


class SystemHealthService:
    def __init__(self, registry: HealthProviderRegistry | None = None) -> None:
        self._registry = registry or get_default_registry()

    def get_summary(self) -> SystemHealthSummary:
        results = self._registry.check_all()
        overall = compute_overall_status(results)
        return SystemHealthSummary(
            overall_status=overall,
            generated_at=_utcnow(),
            environment=environment_name(),
            platform_version=getattr(settings, "app_version", None) or "0.8.9",
            healthy_count=_count(results, HealthStatus.HEALTHY),
            degraded_count=_count(results, HealthStatus.DEGRADED),
            unhealthy_count=_count(results, HealthStatus.UNHEALTHY),
            unknown_count=_count(results, HealthStatus.UNKNOWN),
            services=results,
        )

    def get_metrics(self, *, period: str = "24h") -> SystemMetricsResponse:
        summary = self.get_summary()
        now = _utcnow()
        flat: list[HealthMetric] = []
        for svc in summary.services:
            for m in svc.metrics:
                flat.append(
                    HealthMetric(
                        key=f"{svc.service_id}.{m.key}",
                        label=f"{svc.service_name} — {m.label}",
                        value=m.value,
                        unit=m.unit,
                        status=m.status or svc.status.value,
                        description=m.description,
                        timestamp=now,
                    )
                )
        # Métriques agrégées déterministes
        flat.extend(
            [
                HealthMetric(
                    key="platform.overall_status",
                    label="Statut global",
                    value=summary.overall_status.value,
                    unit=None,
                    status=summary.overall_status.value,
                    description=f"Période {period}",
                    timestamp=now,
                ),
                HealthMetric(
                    key="platform.services_total",
                    label="Services surveillés",
                    value=len(summary.services),
                    unit="services",
                    status=HealthStatus.HEALTHY.value,
                    description=None,
                    timestamp=now,
                ),
            ]
        )
        return SystemMetricsResponse(generated_at=now, period=period, metrics=flat)

    def get_alerts(self) -> SystemAlertsResponse:
        now = _utcnow()
        summary = self.get_summary()
        alerts: list[SystemAlert] = []

        for svc in summary.services:
            if svc.status == HealthStatus.UNHEALTHY:
                alerts.append(
                    SystemAlert(
                        alert_id=f"alert-{svc.service_id}-unhealthy",
                        severity=AlertSeverity.CRITICAL,
                        service_id=svc.service_id,
                        title=f"{svc.service_name} unhealthy",
                        message=svc.summary,
                        impact="Fonctionnalités dépendantes dégradées ou bloquées",
                        recommendation=svc.error_message or "Consulter le runbook du service",
                        started_at=now - timedelta(minutes=25),
                        last_seen_at=now,
                        resolved_at=None,
                        is_active=True,
                    )
                )
            elif svc.status == HealthStatus.DEGRADED:
                alerts.append(
                    SystemAlert(
                        alert_id=f"alert-{svc.service_id}-degraded",
                        severity=AlertSeverity.WARNING,
                        service_id=svc.service_id,
                        title=f"{svc.service_name} degraded",
                        message=svc.summary,
                        impact="Latence ou backlog accru",
                        recommendation="Surveiller la file et les workers",
                        started_at=now - timedelta(minutes=12),
                        last_seen_at=now,
                        resolved_at=None,
                        is_active=True,
                    )
                )

        # Alerte info — rappel mode hybride (pas de monitoring externe)
        simulated = sum(1 for s in summary.services if (s.metadata or {}).get("simulated") is True)
        real = sum(1 for s in summary.services if (s.metadata or {}).get("provider_mode") == "real")
        alerts.append(
            SystemAlert(
                alert_id="alert-platform-health-mode",
                severity=AlertSeverity.INFO,
                service_id=None,
                title="System Health — contrôles internes",
                message=(
                    f"{real} provider(s) réel(s), {simulated} simulé(s). "
                    "Aucun monitoring externe (Prometheus/Grafana/Sentry/OTel)."
                ),
                impact=None,
                recommendation="Activer SYSTEM_HEALTH_*_PROVIDER=real progressivement en staging.",
                started_at=now - timedelta(hours=2),
                last_seen_at=now,
                resolved_at=None,
                is_active=True,
            )
        )

        active = [a for a in alerts if a.is_active]
        return SystemAlertsResponse(
            generated_at=now,
            active_count=len(active),
            critical_count=sum(1 for a in active if a.severity == AlertSeverity.CRITICAL),
            warning_count=sum(1 for a in active if a.severity == AlertSeverity.WARNING),
            alerts=active,
        )

    def get_logs(
        self,
        *,
        limit: int = 100,
        level: str | None = None,
        service_id: str | None = None,
    ) -> SystemLogsResponse:
        now = _utcnow()
        # Journal simulé déterministe
        raw: list[SystemLogEntry] = [
            SystemLogEntry(
                log_id="log-001",
                timestamp=now - timedelta(minutes=1),
                level="info",
                service_id="api",
                event_type="health.check",
                message="Contrôle santé API OK (simulé)",
                correlation_id="corr-rc2-001",
                metadata={"simulated": True},
            ),
            SystemLogEntry(
                log_id="log-002",
                timestamp=now - timedelta(minutes=3),
                level="warning",
                service_id="jobs_queue",
                event_type="queue.backlog",
                message="17 jobs pending — plus vieux 8 minutes (simulé)",
                correlation_id="corr-rc2-002",
                metadata={"pending": 17, "simulated": True},
            ),
            SystemLogEntry(
                log_id="log-003",
                timestamp=now - timedelta(minutes=5),
                level="error",
                service_id="ocr",
                event_type="ocr.unavailable",
                message="OCR désactivé — documents en awaiting_ocr (simulé)",
                correlation_id="corr-rc2-003",
                metadata={"awaiting_ocr": 11, "simulated": True},
            ),
            SystemLogEntry(
                log_id="log-004",
                timestamp=now - timedelta(minutes=8),
                level="info",
                service_id="postgresql",
                event_type="db.ping",
                message="Ping PostgreSQL simulé — 14 ms",
                correlation_id="corr-rc2-004",
                metadata={"latency_ms": 14, "simulated": True},
            ),
            SystemLogEntry(
                log_id="log-005",
                timestamp=now - timedelta(minutes=15),
                level="info",
                service_id="ai",
                event_type="ai.quota",
                message="86 requêtes IA du jour — coût estimé 4.25 EUR (simulé)",
                correlation_id="corr-rc2-005",
                metadata={"simulated": True},
            ),
            SystemLogEntry(
                log_id="log-006",
                timestamp=now - timedelta(minutes=20),
                level="warning",
                service_id="jobs_queue",
                event_type="job.failed",
                message="2 jobs failed dans la fenêtre récente (simulé)",
                correlation_id="corr-rc2-006",
                metadata={"failed": 2, "simulated": True},
            ),
            SystemLogEntry(
                log_id="log-007",
                timestamp=now - timedelta(minutes=30),
                level="info",
                service_id="billing",
                event_type="billing.health",
                message="Billing mock — pas d'appel Stripe réel",
                correlation_id="corr-rc2-007",
                metadata={"simulated": True},
            ),
            SystemLogEntry(
                log_id="log-008",
                timestamp=now - timedelta(minutes=45),
                level="info",
                service_id="vault",
                event_type="vault.health",
                message="Vault simulé opérationnel",
                correlation_id="corr-rc2-008",
                metadata={"simulated": True},
            ),
        ]

        entries = raw
        if level:
            entries = [e for e in entries if e.level.lower() == level.lower()]
        if service_id:
            entries = [e for e in entries if e.service_id == service_id]
        limit = max(1, min(500, int(limit)))
        entries = entries[:limit]
        return SystemLogsResponse(generated_at=now, total=len(entries), entries=entries)
