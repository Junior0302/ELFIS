"""Phase D — Validation comptable (VAL-001 … VAL-005)."""

from __future__ import annotations

from app.accounting.accounting_models import ElfisAccountingEntry, ElfisAccountingProposal, ElfisAccountingReview
from app.accounting.accounting_types import ProposalStatus, ReviewAction
from tests.functional.helpers.phase_d import VALIDATE_BODY, assert_safe_phase_d_body, force_ready_for_validation, seed_accounting_proposal


def test_val_001_validate_balanced(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    user_id = functional_db["seed"]["users"]["org_admin"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, user_id=user_id, force_ready=True)
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert_safe_phase_d_body(body)
    assert body.get("status") == ProposalStatus.VALIDATED or body.get("status") == "validated"

    db = Session()
    try:
        prop = db.query(ElfisAccountingProposal).filter_by(proposal_id=proposal_id).one()
        assert prop.status == ProposalStatus.VALIDATED
        assert prop.validated_at is not None
        assert prop.validated_by_user_id == user_id
        entry = db.query(ElfisAccountingEntry).filter_by(proposal_id=proposal_id).first()
        if entry is not None:
            assert entry.balanced is True
        reviews = db.query(ElfisAccountingReview).filter_by(proposal_id=proposal_id).all()
        assert any(getattr(rv, "action", None) == ReviewAction.VALIDATED or "valid" in str(getattr(rv, "action", "")).lower() for rv in reviews) or len(reviews) >= 1
    finally:
        db.close()


def test_val_002_unbalanced_refused(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-unbal-d", force_ready=True)
        entry = db.query(ElfisAccountingEntry).filter_by(proposal_id=proposal_id).first()
        if entry is not None:
            entry.balanced = False
            entry.total_debit = 100
            entry.total_credit = 50
            db.commit()
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    assert r.status_code in (400, 422)
    assert_safe_phase_d_body(r.json())


def test_val_003_member_refused(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-member-val-d")
    finally:
        db.close()

    api.login_user("member")
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    assert r.status_code in (401, 403)


def test_val_004_other_tenant_refused(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-xtenant-val-d")
    finally:
        db.close()

    api.login_user("other_tenant")
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    assert r.status_code in (403, 404)


def test_val_005_double_validation_idempotent(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-idem-val-d")
    finally:
        db.close()

    api.login_user("org_admin")
    r1 = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    assert r1.status_code in (200, 201)
    r2 = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    )
    assert r2.status_code in (200, 201)
    assert r2.json().get("status") in (ProposalStatus.VALIDATED, "validated")
