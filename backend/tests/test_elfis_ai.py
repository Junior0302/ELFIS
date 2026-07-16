from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.elfis_ai.agents.accounting import run_accounting_agent
from app.elfis_ai.agents.anomaly import run_anomaly_agent
from app.elfis_ai.agents.document_intelligence import run_document_intelligence
from app.elfis_ai.agents.fraud import run_fraud_agent
from app.elfis_ai.history import SupplierHistory, load_supplier_history
from app.elfis_ai.orchestrator import run_elfis_analysis
from app.models import CompanySettings, Invoice
from app.models_saas import User
from app.schemas import AccountingEntry, AccountingLine


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _invoice(**kwargs) -> Invoice:
    defaults = dict(
        organization_id=1,
        filename="f.pdf",
        stored_path="/tmp/f.pdf",
        mime_type="application/pdf",
        supplier="ACME SAS",
        invoice_date="10-07-2026",
        invoice_number="FAC-100",
        amount_ht=100.0,
        amount_tva=20.0,
        amount_ttc=120.0,
        vat_rate=20.0,
        document_type="facture",
        confidence_score=0.9,
        status="ready",
        needs_review=False,
        anomalies="[]",
        missing_fields="[]",
        accounting_entry=AccountingEntry(
            journal="ACH",
            label="Facture FAC-100 — ACME SAS",
            lines=[
                AccountingLine(account="606", label="Achats", debit=100, credit=0),
                AccountingLine(account="44566", label="TVA", debit=20, credit=0),
                AccountingLine(account="401", label="Fournisseur", debit=0, credit=120),
            ],
            explanation="Test",
            imputation="606 — Achats",
        ).model_dump_json(),
        raw_extraction=json.dumps(
            {
                "supplier": "ACME SAS",
                "supplier_iban": "FR7612345678901234567890123",
                "raw_text": "Facture test " * 20,
            }
        ),
    )
    defaults.update(kwargs)
    return Invoice(**defaults)


def test_anomaly_incorrect_total():
    db = _session()
    inv = _invoice(amount_ttc=130.0)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    extraction = run_document_intelligence(inv)
    checks = run_anomaly_agent(db, inv, extraction)
    assert any(a.id == "calc_ht_tva_ttc" for a in checks.anomalies)
    assert any(a.blocking for a in checks.anomalies)


def test_anomaly_zero_vat_ok():
    db = _session()
    inv = _invoice(amount_ht=100.0, amount_tva=0.0, amount_ttc=100.0, vat_rate=0.0)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    checks = run_anomaly_agent(db, inv, run_document_intelligence(inv))
    assert not any(a.id == "calc_ht_tva_ttc" for a in checks.anomalies)


def test_accounting_balanced():
    db = _session()
    inv = _invoice()
    settings = CompanySettings(organization_id=1)
    block = run_accounting_agent(inv, settings)
    assert block.balanced is True
    assert abs(block.total_debit - block.total_credit) < 0.02
    assert any("606" in line.justification for line in block.lines)


def test_duplicate_detection():
    db = _session()
    a = _invoice(invoice_number="DUP-1")
    b = _invoice(invoice_number="DUP-1", filename="other.pdf")
    db.add_all([a, b])
    db.commit()
    db.refresh(a)
    db.refresh(b)
    checks = run_anomaly_agent(db, b, run_document_intelligence(b))
    assert any(a.id == "duplicate_document" for a in checks.anomalies)


def test_iban_change_risk():
    history = SupplierHistory(
        document_count=3,
        amounts=[100.0, 110.0, 105.0],
        dates=["01-01-2026"],
        invoice_numbers=["A"],
        ibans=["FR7600000000000000000000000"],
        anomaly_count=0,
        average_amount=105.0,
        cumulative_amount=315.0,
        last_date="01-01-2026",
    )
    inv = _invoice()
    extraction = run_document_intelligence(inv)
    risk = run_fraud_agent(inv, extraction, history, [])
    assert any(f.code == "iban_change" for f in risk.factors)
    assert "fraude" not in risk.explanation.lower() or "pas une preuve" in risk.explanation.lower()


def test_insufficient_supplier_history():
    db = _session()
    inv = _invoice(supplier="Nouveau Fournisseur XYZ")
    db.add(inv)
    db.commit()
    hist = load_supplier_history(db, organization_id=1, supplier=inv.supplier, exclude_invoice_id=inv.id)
    assert hist.document_count == 0


def test_full_report_json_and_cfo():
    db = _session()
    inv = _invoice()
    db.add(inv)
    db.add(CompanySettings(organization_id=1))
    db.commit()
    db.refresh(inv)
    row = run_elfis_analysis(db, inv, user_id=1)
    report = json.loads(row.report_json)
    assert report["metadata"]["analysis_version"] == "1.0.0"
    assert "cfo_summary" in report
    assert "recommendations" in report
    assert "tax_analysis" in report
    assert "disclaimer" in report["tax_analysis"]
    assert report["summary_card"]["anomaly_count"] >= 0


def test_org_isolation_on_report_route():
    from fastapi import FastAPI

    from app.models_saas import Organization, Subscription
    from app.routers import elfis_ai as elfis_router

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    user = User(
        first_name="Test",
        last_name="User",
        email="elfis-test@example.com",
        status="active",
    )
    org1 = Organization(id=1, name="Org1")
    org2 = Organization(id=2, name="Org2")
    inv = _invoice(organization_id=1)
    db.add_all(
        [
            user,
            org1,
            org2,
            inv,
            CompanySettings(organization_id=1),
            Subscription(organization_id=1, plan="pro", status="active", price=19),
            Subscription(organization_id=2, plan="pro", status="active", price=19),
        ]
    )
    db.commit()
    db.refresh(inv)
    db.refresh(user)
    run_elfis_analysis(db, inv)
    invoice_id = inv.id
    user_id = user.id

    mini = FastAPI()
    mini.include_router(elfis_router.router, prefix="/api")

    def override_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    def make_auth(org_id: int):
        def _auth():
            session = TestingSession()
            u = session.get(User, user_id)
            return AuthContext(
                user=u,
                organization_id=org_id,
                role="admin",
                permissions=["*", "documents.read", "documents.write", "ai.analysis"],
            )

        return _auth

    mini.dependency_overrides[get_db] = override_db
    mini.dependency_overrides[get_auth_context] = make_auth(1)
    mini.dependency_overrides[require_active_subscription] = make_auth(1)

    client = TestClient(mini)
    ok = client.get(f"/api/elfis-ai/documents/{invoice_id}/report")
    assert ok.status_code == 200, ok.text
    assert ok.json()["report"]["metadata"]["document_id"] == invoice_id

    mini.dependency_overrides[get_auth_context] = make_auth(2)
    mini.dependency_overrides[require_active_subscription] = make_auth(2)
    denied = client.get(f"/api/elfis-ai/documents/{invoice_id}/report")
    assert denied.status_code == 404

    mini.dependency_overrides.clear()


def test_invalid_date_anomaly():
    db = _session()
    inv = _invoice(invoice_date="32-13-2026")
    db.add(inv)
    db.commit()
    db.refresh(inv)
    checks = run_anomaly_agent(db, inv, run_document_intelligence(inv))
    assert any(a.id == "invalid_date" for a in checks.anomalies)


def test_devis_no_blocking_accounting_lines_required():
    db = _session()
    entry = AccountingEntry(
        journal="ACH",
        label="Devis",
        lines=[],
        explanation="Devis",
        imputation="Devis",
    )
    inv = _invoice(document_type="devis", accounting_entry=entry.model_dump_json())
    settings = CompanySettings(organization_id=1)
    block = run_accounting_agent(inv, settings)
    assert block.review_required is True
