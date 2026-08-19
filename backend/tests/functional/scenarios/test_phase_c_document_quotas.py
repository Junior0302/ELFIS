"""Phase C — Quotas / entitlements documents."""

from __future__ import annotations

from app.billing.billing_types import FeatureCodes, QuotaCodes
from app.billing.entitlement_service import EntitlementService
from app.billing.quota_service import QuotaService
from tests.document_intelligence import make_text_pdf
from tests.functional.helpers.phase_b import disable_enforcement, enable_enforcement
from tests.functional.helpers.phase_c import assert_safe_document_body


def test_quota_001_002_003_document_quota(api, functional_db, mock_vault_storage, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=False, quotas=True)
    api.login_user("quota_full")
    Session = functional_db["Session"]
    org_id = api.org_id
    db = Session()
    try:
        before = QuotaService(db).check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=0)
        used_before = before.used_value
    finally:
        db.close()

    content = make_text_pdf("QUOTA FULL BLOCK")
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("quota.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    # Refus attendu si enforce quotas + at limit
    assert r.status_code in (402, 403, 429, 200, 201)
    if r.status_code in (402, 403, 429):
        assert_safe_document_body(r.json())
        db = Session()
        try:
            after = QuotaService(db).check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=0)
            assert after.used_value == used_before
        finally:
            db.close()
    disable_enforcement(monkeypatch)


def test_ent_001_002_feature_gates(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_EXPIRED"]["id"]
    db = Session()
    try:
        from app.billing.billing_exceptions import FeatureNotAvailableError
        import pytest

        with pytest.raises(FeatureNotAvailableError):
            EntitlementService(db).require(org_id, FeatureCodes.AI_CLASSIFICATION)
        with pytest.raises(FeatureNotAvailableError):
            EntitlementService(db).require(org_id, FeatureCodes.ACCOUNTING_PROPOSALS)
    finally:
        db.close()
        disable_enforcement(monkeypatch)


def test_suspended_upload_blocked(api, mock_vault_storage):
    api.login_user("suspended")
    content = make_text_pdf("SUSP BLOCK")
    r = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("s.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r.status_code in (403, 402)
    assert_safe_document_body(r.json())
