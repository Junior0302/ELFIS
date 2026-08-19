"""Modes de providers System Health : real | mock | disabled."""

from __future__ import annotations

from typing import Literal

from app.config import settings

ProviderMode = Literal["real", "mock", "disabled"]

VALID_MODES = frozenset({"real", "mock", "disabled"})

# Services pouvant être branchés en réel (étape 2)
REALIZABLE_SERVICE_IDS = frozenset(
    {
        "api",
        "postgresql",
        "jobs_queue",
        "event_bus",
        "search",
        "storage",
        "document_processing",
        "document_ocr",
        "document_extraction",
        "business_validation",
        "product_integrations",
    }
)

# Mapping service_id → attribut Settings
_SERVICE_SETTING_ATTR: dict[str, str] = {
    "api": "system_health_api_provider",
    "postgresql": "system_health_postgres_provider",
    "jobs_queue": "system_health_jobs_provider",
    "event_bus": "system_health_events_provider",
    "search": "system_health_search_provider",
    "storage": "system_health_storage_provider",
    "document_processing": "system_health_document_processing_provider",
    "document_ocr": "system_health_document_ocr_provider",
    "document_extraction": "system_health_document_extraction_provider",
    "business_validation": "system_health_business_validation_provider",
    "product_integrations": "system_health_product_integrations_provider",
}


def normalize_provider_mode(value: str | None) -> ProviderMode:
    raw = (value or "mock").strip().lower()
    if raw not in VALID_MODES:
        return "mock"
    return raw  # type: ignore[return-value]


def resolve_provider_mode(service_id: str, *, settings_obj=None) -> ProviderMode:
    """Résout le mode pour un service.

    Priorité :
    1. Setting par service (SYSTEM_HEALTH_*_PROVIDER)
    2. Si SYSTEM_HEALTH_USE_REAL_PROVIDERS=true et service réalisable → real
    3. sinon mock
    """
    cfg = settings_obj or settings
    attr = _SERVICE_SETTING_ATTR.get(service_id)
    if attr:
        configured = normalize_provider_mode(getattr(cfg, attr, "mock"))
        # Si explicitement mock/disabled, respecter (même si use_real=true)
        # Si "mock" est la valeur par défaut ET use_real=true → real
        use_real = bool(getattr(cfg, "system_health_use_real_providers", False))
        if use_real and service_id in REALIZABLE_SERVICE_IDS:
            # use_real n'écrase que si le setting individuel est encore "mock"
            # (valeur par défaut). Si l'opérateur a forcé disabled, on respecte.
            raw_attr = str(getattr(cfg, attr, "mock") or "mock").strip().lower()
            if raw_attr == "disabled":
                return "disabled"
            if raw_attr == "real":
                return "real"
            if raw_attr == "mock":
                return "real"
        return configured
    return "mock"


def all_provider_modes(*, settings_obj=None) -> dict[str, ProviderMode]:
    modes: dict[str, ProviderMode] = {}
    for sid in REALIZABLE_SERVICE_IDS:
        modes[sid] = resolve_provider_mode(sid, settings_obj=settings_obj)
    return modes
