"""Construction du registry selon la configuration real/mock/disabled."""

from __future__ import annotations

import logging

from app.config import settings
from app.system_health.health_provider_mode import REALIZABLE_SERVICE_IDS, resolve_provider_mode
from app.system_health.health_registry import HealthProviderRegistry
from app.system_health.health_thresholds import load_thresholds
from app.system_health.mock_health_providers import build_mock_providers
from app.system_health.providers.api_health_provider import ApiHealthProvider
from app.system_health.providers.cached_health_provider import CachedHealthProvider
from app.system_health.providers.disabled_health_provider import DisabledHealthProvider
from app.system_health.providers.events_health_provider import EventsHealthProvider
from app.system_health.providers.jobs_health_provider import JobsHealthProvider
from app.system_health.providers.postgresql_health_provider import PostgresqlHealthProvider
from app.system_health.providers.search_health_provider import SearchHealthProvider
from app.system_health.providers.storage_health_provider import StorageHealthProvider

logger = logging.getLogger(__name__)


def _build_real_provider(service_id: str, *, thresholds):
    if service_id == "api":
        return ApiHealthProvider(timeout_seconds=thresholds.provider_timeout_seconds)
    if service_id == "postgresql":
        return PostgresqlHealthProvider(thresholds=thresholds)
    if service_id == "jobs_queue":
        return JobsHealthProvider(thresholds=thresholds)
    if service_id == "event_bus":
        return EventsHealthProvider(thresholds=thresholds)
    if service_id == "search":
        return SearchHealthProvider(thresholds=thresholds)
    if service_id == "storage":
        return StorageHealthProvider(thresholds=thresholds)
    if service_id == "document_processing":
        from app.system_health.providers.document_processing_health_provider import (
            DocumentProcessingHealthProvider,
        )

        return DocumentProcessingHealthProvider()
    if service_id == "document_ocr":
        from app.system_health.providers.document_ocr_health_provider import DocumentOCRHealthProvider

        return DocumentOCRHealthProvider()
    if service_id == "document_extraction":
        from app.system_health.providers.document_extraction_health_provider import (
            DocumentExtractionHealthProvider,
        )

        return DocumentExtractionHealthProvider()
    if service_id == "business_validation":
        from app.system_health.providers.business_validation_health_provider import (
            BusinessValidationHealthProvider,
        )

        return BusinessValidationHealthProvider()
    if service_id == "product_integrations":
        from app.system_health.providers.product_integrations_health_provider import (
            ProductIntegrationsHealthProvider,
        )

        return ProductIntegrationsHealthProvider()
    raise ValueError(f"Pas de provider réel pour {service_id}")


def register_configured_providers(
    registry: HealthProviderRegistry,
    *,
    settings_obj=None,
    wrap_cache: bool = True,
) -> HealthProviderRegistry:
    """Enregistre mocks + remplace les services configurés en real/disabled."""
    cfg = settings_obj or settings
    thresholds = load_thresholds()
    mocks = {p.service_id: p for p in build_mock_providers()}

    for service_id, mock in mocks.items():
        mode = "mock"
        if service_id in REALIZABLE_SERVICE_IDS:
            mode = resolve_provider_mode(service_id, settings_obj=cfg)

        if mode == "disabled":
            provider = DisabledHealthProvider(
                service_id=mock.service_id,
                service_name=mock.service_name,
                category=mock.category,
            )
        elif mode == "real":
            try:
                provider = _build_real_provider(service_id, thresholds=thresholds)
            except Exception as exc:
                logger.warning(
                    "system_health_real_provider_fallback",
                    extra={"service_id": service_id, "error": type(exc).__name__},
                )
                provider = mock
        else:
            provider = mock

        if wrap_cache and mode == "real":
            provider = CachedHealthProvider(provider, ttl_seconds=thresholds.cache_ttl_seconds)

        registry.register(provider)

    return registry


def build_default_registry(*, settings_obj=None) -> HealthProviderRegistry:
    registry = HealthProviderRegistry()
    register_configured_providers(registry, settings_obj=settings_obj)
    return registry
