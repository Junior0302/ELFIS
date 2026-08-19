"""Configuration Security — lit Settings sans secrets exposés."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.security.security_types import RateLimitCategory


@dataclass(frozen=True)
class SecurityConfigSnapshot:
    environment: str
    security_headers_enabled: bool
    csp_enabled: bool
    csp_report_only: bool
    hsts_enabled: bool
    rate_limit_enabled: bool
    rate_limit_backend: str
    jwt_issuer_configured: bool
    jwt_audience_configured: bool
    jwt_issuer_enforced: bool
    metrics_enabled: bool
    metrics_require_auth: bool


def environment_name() -> str:
    raw = (getattr(settings, "elfis_environment", None) or settings.app_env or "development").strip().lower()
    if raw in {"prod", "production"}:
        return "production"
    if raw in {"dev", "development", "local"}:
        return "development"
    if raw in {"test", "testing"}:
        return "test"
    if raw in {"stage", "staging"}:
        return "staging"
    return raw or "development"


def is_production() -> bool:
    return environment_name() == "production"


def is_test() -> bool:
    return environment_name() == "test"


def rate_limit_for(category: RateLimitCategory | str) -> int:
    cat = category.value if isinstance(category, RateLimitCategory) else str(category)
    mapping = {
        RateLimitCategory.AUTH.value: getattr(settings, "elfis_rate_limit_auth_per_minute", 10),
        RateLimitCategory.UPLOAD.value: getattr(settings, "elfis_rate_limit_upload_per_minute", 20),
        RateLimitCategory.AI.value: getattr(settings, "elfis_rate_limit_ai_per_minute", 30),
        RateLimitCategory.SEARCH.value: getattr(settings, "elfis_rate_limit_search_per_minute", 120),
        RateLimitCategory.EMAIL.value: getattr(settings, "elfis_rate_limit_email_per_minute", 30),
        RateLimitCategory.BILLING.value: getattr(settings, "elfis_rate_limit_billing_per_minute", 60),
        RateLimitCategory.PLATFORM_ADMIN.value: getattr(settings, "elfis_rate_limit_admin_per_minute", 120),
        RateLimitCategory.WEBHOOK.value: getattr(settings, "elfis_rate_limit_webhook_per_minute", 300),
        RateLimitCategory.DEFAULT.value: getattr(settings, "elfis_rate_limit_default_per_minute", 120),
    }
    return int(mapping.get(cat, mapping[RateLimitCategory.DEFAULT.value]))


def max_json_body_bytes() -> int:
    return int(getattr(settings, "elfis_max_json_body_bytes", 1_048_576))


def max_upload_bytes() -> int:
    vault_mb = int(getattr(settings, "elfis_vault_max_file_size_mb", 15))
    doc = int(getattr(settings, "elfis_document_max_file_bytes", vault_mb * 1024 * 1024))
    return max(doc, vault_mb * 1024 * 1024)


def configuration_status() -> dict[str, Any]:
    """État non secret pour l'admin plateforme."""
    issuer = (getattr(settings, "elfis_jwt_issuer", "") or "").strip()
    audience = (getattr(settings, "elfis_jwt_audience", "") or "").strip()
    enforce = bool(getattr(settings, "elfis_jwt_enforce_issuer_audience", False))
    return {
        "environment": environment_name(),
        "security_headers": {
            "configured": True,
            "source": "environment",
            "status": "valid" if getattr(settings, "elfis_security_headers_enabled", True) else "warning",
            "enabled": bool(getattr(settings, "elfis_security_headers_enabled", True)),
        },
        "csp": {
            "configured": True,
            "source": "environment",
            "status": "valid",
            "enabled": bool(getattr(settings, "elfis_csp_enabled", True)),
            "report_only": bool(getattr(settings, "elfis_csp_report_only", True)),
        },
        "hsts": {
            "configured": True,
            "source": "environment",
            "status": "valid" if (not is_production() or getattr(settings, "elfis_hsts_enabled", False)) else "warning",
            "enabled": bool(getattr(settings, "elfis_hsts_enabled", False)) and is_production(),
        },
        "rate_limit": {
            "configured": True,
            "source": "environment",
            "status": "valid",
            "enabled": bool(getattr(settings, "elfis_rate_limit_enabled", True)),
            "backend": getattr(settings, "elfis_rate_limit_backend", "memory"),
        },
        "jwt": {
            "configured": True,
            "source": "environment",
            "status": "valid" if len(settings.jwt_secret or "") >= 16 else "warning",
            "issuer_set": bool(issuer),
            "audience_set": bool(audience),
            "enforce_issuer_audience": enforce,
            "clock_skew_seconds": int(getattr(settings, "elfis_jwt_clock_skew_seconds", 30)),
        },
        "cors": {
            "configured": True,
            "source": "environment",
            "status": "error" if (is_production() and settings.cors_origins.strip() == "*") else "valid",
            "wildcard": settings.cors_origins.strip() == "*",
        },
        "metrics": {
            "configured": True,
            "source": "environment",
            "status": "valid",
            "enabled": bool(getattr(settings, "elfis_metrics_enabled", True)),
            "require_auth": bool(getattr(settings, "elfis_metrics_require_auth", True)),
        },
    }


def snapshot() -> SecurityConfigSnapshot:
    issuer = (getattr(settings, "elfis_jwt_issuer", "") or "").strip()
    audience = (getattr(settings, "elfis_jwt_audience", "") or "").strip()
    enforce = bool(getattr(settings, "elfis_jwt_enforce_issuer_audience", False))
    return SecurityConfigSnapshot(
        environment=environment_name(),
        security_headers_enabled=bool(getattr(settings, "elfis_security_headers_enabled", True)),
        csp_enabled=bool(getattr(settings, "elfis_csp_enabled", True)),
        csp_report_only=bool(getattr(settings, "elfis_csp_report_only", True)),
        hsts_enabled=bool(getattr(settings, "elfis_hsts_enabled", False)) and is_production(),
        rate_limit_enabled=bool(getattr(settings, "elfis_rate_limit_enabled", True)),
        rate_limit_backend=str(getattr(settings, "elfis_rate_limit_backend", "memory")),
        jwt_issuer_configured=bool(issuer),
        jwt_audience_configured=bool(audience),
        jwt_issuer_enforced=enforce and bool(issuer) and bool(audience),
        metrics_enabled=bool(getattr(settings, "elfis_metrics_enabled", True)),
        metrics_require_auth=bool(getattr(settings, "elfis_metrics_require_auth", True)),
    )
