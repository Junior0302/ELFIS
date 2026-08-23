"""Validation de configuration au démarrage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.security.security_config import environment_name, is_production


@dataclass
class ConfigIssue:
    level: str  # warning | error | fatal
    code: str
    message: str


def validate_runtime_configuration() -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    env = environment_name()

    secret = settings.jwt_secret or ""
    if secret == "comptapilot-elfis-dev-secret-change-me" or len(secret) < 16:
        level = "fatal" if is_production() else "warning"
        issues.append(
            ConfigIssue(level, "weak_jwt_secret", "JWT_SECRET trop faible ou valeur par défaut")
        )
    elif len(secret) < 32 and is_production():
        issues.append(ConfigIssue("fatal", "weak_jwt_secret", "JWT_SECRET < 32 caractères en production"))

    if is_production() and (not settings.cors_origins.strip() or settings.cors_origins.strip() == "*"):
        issues.append(ConfigIssue("fatal", "cors_wildcard", "CORS_ORIGINS=* interdit en production"))

    if is_production() and settings.database_url.startswith("sqlite"):
        issues.append(ConfigIssue("fatal", "sqlite_in_production", "PostgreSQL requis en production"))

    # Interdit les modes dangereux / mocks en production
    if is_production():
        debug_on = bool(getattr(settings, "debug", False)) or str(
            getattr(settings, "elfis_debug", False)
        ).lower() in {"1", "true", "yes"}
        if debug_on:
            issues.append(ConfigIssue("fatal", "debug_in_production", "DEBUG interdit en production"))

        ocr_provider = (getattr(settings, "elfis_ocr_provider", "") or "").strip().lower()
        if ocr_provider.startswith("mock"):
            issues.append(ConfigIssue("fatal", "mock_ocr_in_production", "Mock OCR interdit en production"))

        ai_provider = (getattr(settings, "elfis_ai_provider", "") or "").strip().lower()
        if ai_provider.startswith("mock"):
            issues.append(ConfigIssue("fatal", "mock_ai_in_production", "Mock AI interdit en production"))

        billing_provider = (getattr(settings, "elfis_billing_provider", "") or "").strip().lower()
        if billing_provider.startswith("mock"):
            issues.append(
                ConfigIssue("fatal", "mock_billing_in_production", "Mock Billing/Stripe interdit en production")
            )

        frontend = (settings.frontend_url or "").lower()
        if "localhost" in frontend or "127.0.0.1" in frontend:
            issues.append(
                ConfigIssue(
                    "fatal",
                    "localhost_frontend_url",
                    "FRONTEND_URL ne doit pas pointer vers localhost en production",
                )
            )

    if is_production() and getattr(settings, "elfis_hsts_enabled", False) is False:
        issues.append(ConfigIssue("warning", "hsts_disabled", "HSTS désactivé en production"))

    if getattr(settings, "elfis_billing_enabled", True):
        if is_production() and not settings.stripe_webhook_secret:
            issues.append(
                ConfigIssue("fatal", "missing_stripe_webhook_secret", "STRIPE_WEBHOOK_SECRET manquant")
            )
        if is_production() and not settings.stripe_secret_key:
            issues.append(ConfigIssue("fatal", "missing_stripe_secret", "STRIPE_SECRET_KEY manquant"))

    if getattr(settings, "elfis_ai_enabled", True) and is_production() and not settings.openai_api_key:
        issues.append(ConfigIssue("warning", "missing_openai_key", "OPENAI_API_KEY manquant (AI actif)"))

    if is_production() and not (settings.supabase_url and settings.supabase_service_role_key):
        issues.append(ConfigIssue("warning", "vault_unconfigured", "Stockage Vault non configuré"))

    if is_production() and not settings.platform_admin_email_set:
        issues.append(ConfigIssue("fatal", "no_platform_admin", "PLATFORM_ADMIN_EMAILS vide"))

    allow_creds = bool(getattr(settings, "elfis_allow_credentials", True))
    if settings.cors_origins.strip() == "*" and allow_creds and env != "development":
        issues.append(
            ConfigIssue(
                "fatal" if is_production() else "warning",
                "cors_credentials_wildcard",
                "CORS * incompatible avec credentials hors développement",
            )
        )

    return issues


def assert_startup_configuration() -> dict[str, Any]:
    issues = validate_runtime_configuration()
    fatals = [i for i in issues if i.level == "fatal"]
    result = {
        "environment": environment_name(),
        "issues": [{"level": i.level, "code": i.code, "message": i.message} for i in issues],
        "ok": not fatals,
    }
    if fatals and is_production():
        messages = "; ".join(f.message for f in fatals)
        raise RuntimeError(f"Configuration production invalide: {messages}")
    return result


def configuration_public_view() -> dict[str, Any]:
    """Sans secrets — pour admin plateforme."""
    from app.security.security_config import configuration_status

    issues = validate_runtime_configuration()
    return {
        "environment": environment_name(),
        "protections": configuration_status(),
        "issues": [
            {"level": i.level, "code": i.code, "message": i.message, "status": i.level}
            for i in issues
        ],
    }
