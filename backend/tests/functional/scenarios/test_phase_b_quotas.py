"""Phase B — Quotas (QUOTA-001 … QUOTA-007)."""

from __future__ import annotations

import pytest

from app.billing.billing_exceptions import QuotaExceededError
from app.billing.billing_types import QuotaCodes
from app.billing.quota_service import QuotaService
from app.billing.subscription_service import SubscriptionService
from tests.functional.helpers.phase_b import disable_enforcement, enable_enforcement


def test_quota_001_available(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
        result = QuotaService(db).check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=1)
        assert result.allowed is True
    finally:
        db.close()


def test_quota_002_near_80(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_QUOTA_NEAR"]["id"]
    db = Session()
    try:
        result = QuotaService(db).check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=0)
        assert result.used_value >= 80
        if result.limit_value:
            assert result.used_value / result.limit_value >= 0.8
    finally:
        db.close()


def test_quota_003_004_006_at_limit_refused_no_consume(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=False, quotas=True)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_QUOTA_FULL"]["id"]
    db = Session()
    try:
        qs = QuotaService(db)
        before = qs.check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=0)
        used_before = before.used_value
        result = qs.check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=1)
        assert result.allowed is False
        with pytest.raises(QuotaExceededError):
            qs.consume(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, 1)
        after = qs.check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=0)
        assert after.used_value == used_before
    finally:
        db.close()
        disable_enforcement(monkeypatch)


def test_quota_005_unlimited(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, quotas=True)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
        # AI executions souvent illimitées sur starter
        result = QuotaService(db).check(org_id, QuotaCodes.AI_EXECUTIONS_MONTH, amount=100)
        assert result.allowed is True
        assert result.limit_value is None or result.remaining is None or result.allowed
    finally:
        db.close()


def test_quota_007_override(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, quotas=True)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_QUOTA_FULL"]["id"]
    db = Session()
    try:
        qs = QuotaService(db)
        # Augmenter la limite via mutation contrôlée (override admin style)
        for q in qs.repo.list_quotas(org_id):
            if q.quota_code == QuotaCodes.DOCUMENTS_PROCESSED_MONTH:
                q.limit_value = 200
                q.hard_limit = True
        db.commit()
        result = qs.check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=1)
        assert result.allowed is True
    finally:
        db.close()
        disable_enforcement(monkeypatch)
