"""Tests Accounting Engine V2 — fondation."""

from __future__ import annotations

from app.accounting_engine.enums import JournalCode, ProposalV2Status
from app.accounting_engine.exceptions import EngineNotFoundError
from app.accounting_engine.learning import LearningEngine
from app.accounting_engine.proposal_service import ProposalService
from app.accounting_engine.vat_engine import VATEngine
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.models import CompanySettings, Invoice
from tests.document_intake.conftest_helpers import make_intake_db, seed_org_user


def _bootstrap():
    factory, _ = make_intake_db()
    from app.accounting_engine import models as ae  # noqa: F401

    db = factory()
    engine = db.get_bind()
    for tbl in (
        CompanySettings.__table__,
        Invoice.__table__,
        ae.ElfisChartOfAccount.__table__,
        ae.ElfisAccountingEngineProposal.__table__,
        ae.ElfisAccountingLearningMemory.__table__,
        ae.ElfisAccountingEngineAudit.__table__,
    ):
        tbl.create(bind=engine, checkfirst=True)
    org, user = seed_org_user(db)
    return db, org, user


def _purchase_payload(**kw):
    base = {
        "document_type": "invoice",
        "document_number": "FA-100",
        "document_date": "2024-01-15",
        "supplier_name": "ACME SARL",
        "amount_ht": 100,
        "amount_vat": 20,
        "amount_ttc": 120,
        "vat_rate": 20,
        "currency": "EUR",
        "extraction_confidence": 0.8,
        "validation_confidence": 0.9,
    }
    base.update(kw)
    return base


def test_vat_engine_and_exempt():
    r = VATEngine().compute(amount_ht=100, amount_vat=20, amount_ttc=120, vat_rate=20)
    assert float(r.amount_ttc) == 120.0
    assert not r.errors
    ex = VATEngine().compute(amount_ht=50, exempt=True)
    assert float(ex.amount_vat) == 0.0


def test_purchase_invoice_proposal():
    db, org, user = _bootstrap()
    svc = ProposalService(db)
    row = svc.generate(
        organization_id=org.id,
        actor_user_id=user.id,
        payload=_purchase_payload(),
        source_document_id="doc-purchase-1",
    )
    assert row.journal_code == JournalCode.ACH.value
    assert row.confidence_score is not None
    assert row.lines_json
    assert abs(sum(l["debit"] for l in row.lines_json) - sum(l["credit"] for l in row.lines_json)) < 0.05
    assert row.status in {
        ProposalV2Status.GENERATED.value,
        ProposalV2Status.REQUIRES_REVIEW.value,
    }
    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.ACCOUNTING_ENGINE_PROPOSAL_GENERATED in names or (
        EventNames.ACCOUNTING_ENGINE_PROPOSAL_REQUIRES_REVIEW in names
    )
    db.close()


def test_sales_invoice_and_credit_note():
    db, org, user = _bootstrap()
    svc = ProposalService(db)
    sale = svc.generate(
        organization_id=org.id,
        actor_user_id=user.id,
        payload=_purchase_payload(
            document_type="customer_invoice",
            direction="sale",
            customer_name="Client SA",
            supplier_name=None,
        ),
        source_document_id="doc-sale-1",
    )
    assert sale.journal_code == JournalCode.VTE.value

    credit = svc.generate(
        organization_id=org.id,
        actor_user_id=user.id,
        payload=_purchase_payload(document_type="credit_note", document_number="AV-1"),
        source_document_id="doc-credit-1",
    )
    assert credit.journal_code == JournalCode.ACH.value
    assert credit.lines_json
    db.close()


def test_no_vat_and_multi_line_consistency():
    db, org, user = _bootstrap()
    svc = ProposalService(db)
    row = svc.generate(
        organization_id=org.id,
        actor_user_id=user.id,
        payload=_purchase_payload(
            amount_ht=80, amount_vat=0, amount_ttc=80, vat_rate=0, vat_exempt=True
        ),
        source_document_id="doc-novat",
    )
    assert row.amount_vat == 0 or row.amount_vat == 0.0
    assert "tva" in " ".join(row.warnings_json or []).lower() or row.amount_vat == 0
    cons = row.consistency_json or {}
    assert "balanced" in cons
    db.close()


def test_regenerate_confidence_explanation_learning():
    db, org, user = _bootstrap()
    svc = ProposalService(db)
    row = svc.generate(
        organization_id=org.id,
        actor_user_id=user.id,
        payload=_purchase_payload(),
        source_document_id="doc-learn",
    )
    conf = svc.confidence(organization_id=org.id, proposal_id=row.id)
    assert conf["score"] is not None
    expl = svc.explanation(organization_id=org.id, proposal_id=row.id)
    assert "explanations" in expl
    assert "comparison" in expl

    regen = svc.regenerate(
        organization_id=org.id,
        proposal_id=row.id,
        actor_user_id=user.id,
    )
    assert regen.version >= 2
    assert regen.id != row.id

    svc.remember_validation(
        organization_id=org.id, proposal_id=regen.id, actor_user_id=user.id
    )
    hints = LearningEngine(db).lookup(
        organization_id=org.id,
        direction="purchase",
        document_type="invoice",
        party_name="ACME SARL",
    )
    assert hints  # historique présent

    # 2e génération doit pouvoir utiliser l'historique
    row2 = svc.generate(
        organization_id=org.id,
        actor_user_id=user.id,
        payload=_purchase_payload(document_number="FA-200"),
        source_document_id="doc-learn-2",
    )
    assert row2.confidence_detail_json
    db.close()


def test_cross_tenant_and_permissions_catalog():
    db, org, user = _bootstrap()
    org2, _ = seed_org_user(db, email="ae2@test.local", name="Other")
    svc = ProposalService(db)
    row = svc.generate(
        organization_id=org.id,
        actor_user_id=user.id,
        payload=_purchase_payload(),
        source_document_id="doc-tenant",
    )
    try:
        svc.get_proposal(organization_id=org2.id, proposal_id=row.id)
        assert False
    except EngineNotFoundError:
        pass

    from app.accounting_engine.permissions import ACCOUNTING_ENGINE_PERMISSIONS
    from app.iam.permission_catalog import Permission

    for p in ACCOUNTING_ENGINE_PERMISSIONS:
        assert Permission(p).value == p
    db.close()


def test_from_invoice_model():
    db, org, user = _bootstrap()
    inv = Invoice(
        organization_id=org.id,
        filename="f.pdf",
        stored_path="/tmp/f.pdf",
        supplier="Fournisseur X",
        invoice_number="INV-9",
        invoice_date="15-01-2024",
        amount_ht=200,
        amount_tva=40,
        amount_ttc=240,
        vat_rate=20,
        document_type="invoice",
        status="imported",
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    row = ProposalService(db).generate(
        organization_id=org.id,
        actor_user_id=user.id,
        invoice_id=inv.id,
    )
    assert row.source_kind == "invoice"
    assert row.amount_ttc == 240
    db.close()
