"""ENV — validation configuration production."""

from __future__ import annotations

from tests.production_readiness.helpers import fatal_codes, issues_for_production_simulation


def test_env_001_production_refuses_sqlite(monkeypatch):
    issues = issues_for_production_simulation(
        monkeypatch,
        database_url="sqlite:///./prod.db",
        jwt_secret="x" * 40,
        cors_origins="https://elfis-core.com",
        stripe_secret_key="sk_live_fake_for_test_only_not_real",
        stripe_webhook_secret="whsec_fake_for_test_only",
        platform_admin_emails="admin@example.com",
        frontend_url="https://elfis-core.com",
        elfis_billing_provider="stripe",
        elfis_ai_provider="openai",
        elfis_ocr_provider="disabled",
    )
    assert "sqlite_in_production" in fatal_codes(issues)


def test_env_002_003_refuses_mocks(monkeypatch):
    issues = issues_for_production_simulation(
        monkeypatch,
        database_url="postgresql://user:pass@localhost/elfis",
        jwt_secret="x" * 40,
        cors_origins="https://elfis-core.com",
        stripe_secret_key="sk_live_fake",
        stripe_webhook_secret="whsec_fake",
        platform_admin_emails="admin@example.com",
        frontend_url="https://elfis-core.com",
        elfis_billing_provider="mock",
        elfis_ai_provider="openai",
        elfis_ocr_provider="disabled",
    )
    assert "mock_billing_in_production" in fatal_codes(issues)


def test_env_004_requires_strong_jwt(monkeypatch):
    issues = issues_for_production_simulation(
        monkeypatch,
        database_url="postgresql://user:pass@localhost/elfis",
        jwt_secret="short",
        cors_origins="https://elfis-core.com",
        stripe_secret_key="sk_live_fake",
        stripe_webhook_secret="whsec_fake",
        platform_admin_emails="admin@example.com",
        frontend_url="https://elfis-core.com",
        elfis_billing_provider="stripe",
        elfis_ai_provider="openai",
        elfis_ocr_provider="disabled",
    )
    assert "weak_jwt_secret" in fatal_codes(issues)


def test_env_005_refuses_cors_wildcard(monkeypatch):
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
    )
    assert "cors_wildcard" in fatal_codes(issues) or "cors_credentials_wildcard" in fatal_codes(issues)


def test_env_006_seed_refuses_production():
    from tests.functional.seed import assert_safe_environment

    raised = False
    try:
        assert_safe_environment(database_url="postgresql://x/test", environment="production")
    except RuntimeError:
        raised = True
    assert raised
