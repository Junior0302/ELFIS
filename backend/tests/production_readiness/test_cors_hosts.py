"""CORS / trusted hosts — garde-fous production."""

from __future__ import annotations

from tests.production_readiness.helpers import fatal_codes, issues_for_production_simulation


def test_cors_wildcard_forbidden_production(monkeypatch):
    issues = issues_for_production_simulation(
        monkeypatch,
        database_url="postgresql://user:pass@localhost/elfis",
        jwt_secret="x" * 40,
        cors_origins="*",
        stripe_secret_key="sk_live_fake",
        stripe_webhook_secret="whsec_fake",
        platform_admin_emails="admin@example.com",
        frontend_url="https://elfis-core.com",
        elfis_billing_provider="stripe",
        elfis_ai_provider="openai",
        elfis_ocr_provider="disabled",
        elfis_allow_credentials=True,
    )
    codes = fatal_codes(issues)
    assert "cors_wildcard" in codes or "cors_credentials_wildcard" in codes


def test_cors_explicit_origin_ok(monkeypatch):
    issues = issues_for_production_simulation(
        monkeypatch,
        database_url="postgresql://user:pass@localhost/elfis",
        jwt_secret="x" * 40,
        cors_origins="https://elfis-core.com,https://app.elfis-core.com",
        stripe_secret_key="sk_live_fake",
        stripe_webhook_secret="whsec_fake",
        platform_admin_emails="admin@example.com",
        frontend_url="https://elfis-core.com",
        elfis_billing_provider="stripe",
        elfis_ai_provider="openai",
        elfis_ocr_provider="disabled",
        openai_api_key="sk-fake-not-real",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="fake_service_role",
    )
    assert "cors_wildcard" not in fatal_codes(issues)
