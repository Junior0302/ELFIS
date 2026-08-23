"""Gate ELFIS_DEMO_BANK_ENABLED — Banque Démo uniquement si activée."""

from __future__ import annotations

from app.banking.demo_gate import DEMO_PROVIDER, FICTIONAL_BANK_LABEL, is_demo_bank_enabled
from app.banking.engine import BankingEngine, BankingEngineError
from app.config import settings

from tests.banking.conftest_helpers import make_banking_db, seed_org


def test_demo_bank_enabled_by_default_outside_production(monkeypatch):
    monkeypatch.setattr(settings, "elfis_demo_bank_enabled", None)
    monkeypatch.setattr(settings, "elfis_environment", "development")
    monkeypatch.setattr(settings, "app_env", "development")
    assert is_demo_bank_enabled() is True


def test_demo_bank_disabled_by_default_in_production(monkeypatch):
    monkeypatch.setattr(settings, "elfis_demo_bank_enabled", None)
    monkeypatch.setattr(settings, "elfis_environment", "production")
    monkeypatch.setattr(settings, "app_env", "production")
    assert is_demo_bank_enabled() is False


def test_demo_bank_can_be_enabled_in_production(monkeypatch):
    monkeypatch.setattr(settings, "elfis_demo_bank_enabled", True)
    monkeypatch.setattr(settings, "elfis_environment", "production")
    assert is_demo_bank_enabled() is True


def test_available_connectors_hide_demo_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "elfis_demo_bank_enabled", False)
    db = make_banking_db()
    try:
        providers = {item["provider"] for item in BankingEngine(db).available_connectors()}
        assert DEMO_PROVIDER not in providers
        assert "bridge" in providers
    finally:
        db.close()


def test_available_connectors_mark_demo_as_fictional(monkeypatch):
    monkeypatch.setattr(settings, "elfis_demo_bank_enabled", True)
    db = make_banking_db()
    try:
        demo = next(
            item
            for item in BankingEngine(db).available_connectors()
            if item["provider"] == DEMO_PROVIDER
        )
        assert demo["fictional"] is True
        assert demo["display_name"] == FICTIONAL_BANK_LABEL
        assert demo["message"] == FICTIONAL_BANK_LABEL
    finally:
        db.close()


def test_connect_demo_refused_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "elfis_demo_bank_enabled", False)
    db = make_banking_db()
    org = seed_org(db)
    try:
        engine = BankingEngine(db)
        try:
            engine.connect(organization_id=org.id, provider=DEMO_PROVIDER)
            raised = False
        except BankingEngineError as exc:
            raised = True
            assert "désactivée" in str(exc)
        assert raised
    finally:
        db.close()
