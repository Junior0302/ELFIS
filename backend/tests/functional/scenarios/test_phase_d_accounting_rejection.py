"""Phase D — Rejet comptable (REJECT-001 … REJECT-003)."""

from __future__ import annotations

from app.accounting.accounting_models import ElfisAccountingProposal
from app.accounting.accounting_types import ProposalStatus
from tests.functional.helpers.phase_d import VALIDATE_BODY, assert_safe_phase_d_body, seed_accounting_proposal


def test_reject_001_with_reason(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-rej-1")
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/reject",
        headers=api._headers(),
        json={"reason": "Montants incorrects — Phase D"},
    )
    assert r.status_code in (200, 201), r.text
    assert_safe_phase_d_body(r.json())
    db = Session()
    try:
        prop = db.query(ElfisAccountingProposal).filter_by(proposal_id=proposal_id).one()
        assert prop.status == ProposalStatus.REJECTED
    finally:
        db.close()


def test_reject_002_without_reason_refused(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-rej-2")
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/reject",
        headers=api._headers(),
        json={"reason": ""},
    )
    assert r.status_code in (400, 422)


def test_reject_003_after_validation_refused(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(db, org_id=org_id, vault_id="vd-rej-3")
    finally:
        db.close()

    api.login_user("org_admin")
    assert api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json=VALIDATE_BODY,
    ).status_code in (200, 201)
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/reject",
        headers=api._headers(),
        json={"reason": "Trop tard"},
    )
    assert r.status_code in (400, 409)
    assert_safe_phase_d_body(r.json())
