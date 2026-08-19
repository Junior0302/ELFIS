"""PROVIDER — configuration sans réseau."""

from __future__ import annotations


def test_provider_001_fastapi_import_no_network():
    """L’import FastAPI ne doit pas exiger Internet."""
    from app.main import app

    assert app is not None
    assert len(app.routes) > 0


def test_provider_002_stripe_missing_secret_fatal_in_prod(monkeypatch):
    from tests.production_readiness.helpers import fatal_codes, issues_for_production_simulation

    issues = issues_for_production_simulation(
        monkeypatch,
        database_url="postgresql://user:pass@localhost/elfis",
        jwt_secret="x" * 40,
        cors_origins="https://elfis-core.com",
        stripe_secret_key="",
        stripe_webhook_secret="whsec_fake",
        platform_admin_emails="admin@example.com",
        frontend_url="https://elfis-core.com",
        elfis_billing_provider="stripe",
        elfis_billing_enabled=True,
        elfis_ai_provider="openai",
        elfis_ocr_provider="disabled",
    )
    assert "missing_stripe_secret" in fatal_codes(issues)


def test_provider_003_ai_mock_forbidden(monkeypatch):
    from tests.production_readiness.helpers import fatal_codes, issues_for_production_simulation

    issues = issues_for_production_simulation(
        monkeypatch,
        database_url="postgresql://user:pass@localhost/elfis",
        jwt_secret="x" * 40,
        cors_origins="https://elfis-core.com",
        stripe_secret_key="sk_live_fake",
        stripe_webhook_secret="whsec_fake",
        platform_admin_emails="admin@example.com",
        frontend_url="https://elfis-core.com",
        elfis_billing_provider="stripe",
        elfis_ai_provider="mock",
        elfis_ocr_provider="disabled",
    )
    assert "mock_ai_in_production" in fatal_codes(issues)


def test_provider_004_mailer_status_does_not_call_network():
    from app.services.mailer import email_configured, email_status_public

    # Lecture config locale uniquement
    _ = email_configured()
    status = email_status_public()
    assert isinstance(status, dict)


def test_provider_005_storage_warning_without_supabase(monkeypatch):
    from tests.production_readiness.helpers import issues_for_production_simulation

    issues = issues_for_production_simulation(
        monkeypatch,
        database_url="postgresql://user:pass@localhost/elfis",
        jwt_secret="x" * 40,
        cors_origins="https://elfis-core.com",
        stripe_secret_key="sk_live_fake",
        stripe_webhook_secret="whsec_fake",
        platform_admin_emails="admin@example.com",
        frontend_url="https://elfis-core.com",
        elfis_billing_provider="stripe",
        elfis_ai_provider="openai",
        elfis_ocr_provider="disabled",
        supabase_url="",
        supabase_service_role_key="",
    )
    codes = {i.code for i in issues}
    assert "vault_unconfigured" in codes
