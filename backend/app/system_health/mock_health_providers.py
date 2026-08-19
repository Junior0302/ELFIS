"""Providers de santé simulés RC2.1 — valeurs déterministes (pas de random)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.system_health.health_provider import HealthProvider
from app.system_health.health_registry import HealthProviderRegistry
from app.system_health.health_schemas import HealthCheckResult, HealthMetric
from app.system_health.health_types import HealthCategory, HealthStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _metric(
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
        timestamp=_utcnow(),
    )


class FixedHealthProvider(HealthProvider):
    """Provider mock avec résultat fixe."""

    def __init__(
        self,
        *,
        service_id: str,
        service_name: str,
        category: str,
        status: HealthStatus,
        summary: str,
        latency_ms: float | None = None,
        version: str | None = None,
        metrics: list[HealthMetric] | None = None,
        metadata: dict | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.service_id = service_id
        self.service_name = service_name
        self.category = category
        self._status = status
        self._summary = summary
        self._latency_ms = latency_ms
        self._version = version
        self._metrics = metrics or []
        self._metadata = metadata or {}
        self._error_code = error_code
        self._error_message = error_message

    def check_health(self) -> HealthCheckResult:
        return HealthCheckResult(
            service_id=self.service_id,
            service_name=self.service_name,
            category=self.category,
            status=self._status,
            summary=self._summary,
            latency_ms=self._latency_ms,
            checked_at=_utcnow(),
            version=self._version,
            metrics=list(self._metrics),
            metadata=dict(self._metadata),
            error_code=self._error_code,
            error_message=self._error_message,
        )


class ExplodingHealthProvider(HealthProvider):
    """Provider de test qui lève une exception."""

    service_id = "exploding"
    service_name = "Exploding (test)"
    category = HealthCategory.PLATFORM.value

    def check_health(self) -> HealthCheckResult:
        raise RuntimeError("boom_simulated")


def build_mock_providers() -> list[HealthProvider]:
    return [
        FixedHealthProvider(
            service_id="api",
            service_name="API FastAPI",
            category=HealthCategory.PLATFORM.value,
            status=HealthStatus.HEALTHY,
            summary="API disponible — latence nominale",
            latency_ms=42.0,
            version="1.0.0-rc1",
            metrics=[
                _metric("requests_24h", "Requêtes (24h)", 12840, unit="req"),
                _metric("p95_ms", "Latence p95", 58, unit="ms", status=HealthStatus.HEALTHY.value),
                _metric("error_rate", "Taux 5xx", 0.12, unit="%"),
            ],
            metadata={"simulated": True},
        ),
        FixedHealthProvider(
            service_id="postgresql",
            service_name="PostgreSQL",
            category=HealthCategory.DATA.value,
            status=HealthStatus.HEALTHY,
            summary="Base accessible — pool stable",
            latency_ms=14.0,
            version="17.6",
            metrics=[
                _metric("active_connections", "Connexions actives", 7, unit="conn"),
                _metric("pool_size", "Taille du pool", 5, unit="conn"),
                _metric("max_overflow", "Overflow max", 10, unit="conn"),
            ],
            metadata={"simulated": True, "engine": "postgresql"},
        ),
        FixedHealthProvider(
            service_id="jobs_queue",
            service_name="Jobs Queue",
            category=HealthCategory.WORKERS.value,
            status=HealthStatus.DEGRADED,
            summary="File en retard — 17 jobs pending",
            latency_ms=35.0,
            version="v1",
            metrics=[
                _metric("pending", "Jobs pending", 17, unit="jobs", status=HealthStatus.DEGRADED.value),
                _metric("failed", "Jobs failed", 2, unit="jobs", status=HealthStatus.DEGRADED.value),
                _metric("oldest_pending_minutes", "Plus vieux pending", 8, unit="min"),
            ],
            metadata={"simulated": True},
        ),
        FixedHealthProvider(
            service_id="event_bus",
            service_name="Event Bus",
            category=HealthCategory.WORKERS.value,
            status=HealthStatus.HEALTHY,
            summary="Bus opérationnel — claim nominal",
            latency_ms=22.0,
            version="v1",
            metrics=[
                _metric("pending_events", "Events pending", 3, unit="events"),
                _metric("processed_24h", "Traités (24h)", 940, unit="events"),
            ],
            metadata={"simulated": True},
        ),
        FixedHealthProvider(
            service_id="search",
            service_name="Search",
            category=HealthCategory.SEARCH.value,
            status=HealthStatus.HEALTHY,
            summary="Index Search disponible",
            latency_ms=48.0,
            version="v1",
            metrics=[
                _metric("indexed_docs", "Documents indexés", 1250, unit="docs"),
                _metric("query_p95_ms", "Query p95", 65, unit="ms"),
            ],
            metadata={"simulated": True},
        ),
        FixedHealthProvider(
            service_id="billing",
            service_name="Billing",
            category=HealthCategory.BILLING.value,
            status=HealthStatus.HEALTHY,
            summary="Billing opérationnel (mode simulé)",
            latency_ms=30.0,
            version="v1",
            metrics=[
                _metric("active_subscriptions", "Abonnements actifs", 42, unit="subs"),
                _metric("webhooks_24h", "Webhooks (24h)", 18, unit="events"),
            ],
            metadata={"simulated": True, "provider_mode": "mock"},
        ),
        FixedHealthProvider(
            service_id="notifications",
            service_name="Notifications",
            category=HealthCategory.COMMUNICATION.value,
            status=HealthStatus.HEALTHY,
            summary="Canal notifications OK",
            latency_ms=28.0,
            version="v1",
            metrics=[
                _metric("sent_24h", "Envoyées (24h)", 310, unit="notif"),
                _metric("failed_24h", "Échecs (24h)", 1, unit="notif"),
            ],
            metadata={"simulated": True},
        ),
        FixedHealthProvider(
            service_id="authentication",
            service_name="Authentication",
            category=HealthCategory.SECURITY.value,
            status=HealthStatus.HEALTHY,
            summary="Auth JWT / Firebase mapping OK",
            latency_ms=18.0,
            version="v1",
            metrics=[
                _metric("logins_24h", "Connexions (24h)", 560, unit="auth"),
                _metric("denied_24h", "Refus (24h)", 4, unit="auth"),
            ],
            metadata={"simulated": True},
        ),
        FixedHealthProvider(
            service_id="vault",
            service_name="Vault",
            category=HealthCategory.STORAGE.value,
            status=HealthStatus.HEALTHY,
            summary="Vault documentaire opérationnel",
            latency_ms=55.0,
            version="v1",
            metrics=[
                _metric("documents", "Documents", 890, unit="docs"),
                _metric("archives_24h", "Archives (24h)", 24, unit="docs"),
            ],
            metadata={"simulated": True},
        ),
        FixedHealthProvider(
            service_id="storage",
            service_name="Storage",
            category=HealthCategory.STORAGE.value,
            status=HealthStatus.HEALTHY,
            summary="Stockage objet (simulé) — bucket configuré",
            latency_ms=40.0,
            version="v1",
            metrics=[
                _metric("objects", "Objets", 890, unit="obj"),
                _metric("signed_url_ttl_s", "TTL URL signée", 300, unit="s"),
            ],
            metadata={"simulated": True, "provider_mode": "mock"},
        ),
        FixedHealthProvider(
            service_id="document_processing",
            service_name="Document Processing",
            category=HealthCategory.WORKERS.value,
            status=HealthStatus.HEALTHY,
            summary="File processing nominale (simulé)",
            latency_ms=25.0,
            version="v1",
            metrics=[
                _metric("queued", "Jobs queued", 2, unit="jobs"),
                _metric("running", "Jobs running", 1, unit="jobs"),
                _metric("failed_1h", "Failed 1h", 0, unit="jobs"),
                _metric("expired_leases", "Leases expirées", 0, unit="jobs"),
                _metric("oldest_queued_age", "Oldest queued age", 12, unit="s"),
            ],
            metadata={"simulated": True, "provider_mode": "mock"},
        ),
        FixedHealthProvider(
            service_id="document_ocr",
            service_name="Document OCR",
            category=HealthCategory.OCR.value,
            status=HealthStatus.HEALTHY,
            summary="OCR framework (noop simulé)",
            latency_ms=20.0,
            version="v1",
            metrics=[
                _metric("enabled", "OCR enabled", 0),
                _metric("queued", "OCR jobs queued", 0, unit="jobs"),
                _metric("failed_24h", "OCR failed 24h", 0, unit="results"),
            ],
            metadata={"simulated": True, "provider_mode": "mock", "real_ocr": False},
        ),
        FixedHealthProvider(
            service_id="document_extraction",
            service_name="Document Extraction",
            category=HealthCategory.OCR.value,
            status=HealthStatus.HEALTHY,
            summary="Extraction framework (noop simulé)",
            latency_ms=22.0,
            version="v1",
            metrics=[
                _metric("enabled", "Extraction enabled", 0),
                _metric("requires_review", "Requires review", 0, unit="results"),
                _metric("queued_jobs", "Extraction jobs queued", 0, unit="jobs"),
            ],
            metadata={"simulated": True, "provider_mode": "mock", "real_extraction": False},
        ),
        FixedHealthProvider(
            service_id="business_validation",
            service_name="Business Validation",
            category=HealthCategory.OCR.value,
            status=HealthStatus.HEALTHY,
            summary="Validation métier documentaire (simulé)",
            latency_ms=18.0,
            version="v1",
            metrics=[
                _metric("enabled", "BV enabled", 0),
                _metric("invalid_1h", "Invalid 1h", 0, unit="results"),
                _metric("queued_jobs", "BV jobs queued", 0, unit="jobs"),
            ],
            metadata={"simulated": True, "provider_mode": "mock"},
        ),
        FixedHealthProvider(
            service_id="product_integrations",
            service_name="Product Integrations",
            category=HealthCategory.WORKERS.value,
            status=HealthStatus.HEALTHY,
            summary="Bridge produit désactivé (simulé)",
            latency_ms=15.0,
            version="v1",
            metrics=[
                _metric("bridge_enabled", "Bridge enabled", 0),
                _metric("queued_deliveries", "Queued deliveries", 0, unit="jobs"),
            ],
            metadata={"simulated": True, "provider_mode": "mock", "disabled_by_config": True},
        ),
        FixedHealthProvider(
            service_id="ai",
            service_name="AI Engine",
            category=HealthCategory.AI.value,
            status=HealthStatus.HEALTHY,
            summary="Moteur IA disponible (simulé)",
            latency_ms=320.0,
            version="v1",
            metrics=[
                _metric("requests_today", "Requêtes du jour", 86, unit="req"),
                _metric("avg_latency_ms", "Latence moyenne", 320, unit="ms"),
                _metric("estimated_cost_eur", "Coût estimé", 4.25, unit="EUR"),
            ],
            metadata={"simulated": True, "provider_mode": "mock"},
        ),
        FixedHealthProvider(
            service_id="ocr",
            service_name="OCR",
            category=HealthCategory.OCR.value,
            status=HealthStatus.UNHEALTHY,
            summary="OCR indisponible — documents en awaiting_ocr",
            latency_ms=None,
            version="disabled",
            metrics=[
                _metric("awaiting_ocr", "Documents awaiting OCR", 11, unit="docs", status=HealthStatus.UNHEALTHY.value),
                _metric("enabled", "OCR activé", "false"),
            ],
            metadata={"simulated": True, "provider_mode": "disabled"},
            error_code="ocr_disabled",
            error_message="OCR désactivé par configuration (ELFIS_OCR_ENABLED=false)",
        ),
    ]


def register_mock_providers(registry: HealthProviderRegistry) -> None:
    for provider in build_mock_providers():
        registry.register(provider)
