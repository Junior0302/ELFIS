"""Helpers de test Financial Dashboard V1 — base SQLite mémoire + jeu de données."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models  # noqa: F401
from app import models_saas  # noqa: F401
from app.banking import banking_models  # noqa: F401
from app.events import event_models  # noqa: F401
from app.ai_assistant import models as ai_assistant_models  # noqa: F401
from app.financial.cache import reset_change_tracking, snapshot_cache
from app.models import BankAccount, BankTransaction, Invoice
from app.models_saas import Organization, SalesDocument

# Calé sur la date réelle : le moteur bucketise par rapport à date.today()
TODAY = date.today()


def make_financial_db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    snapshot_cache.clear()
    reset_change_tracking()
    return sessionmaker(bind=engine)()


def seed_org(db: Session, name: str = "Org Finance") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _iso(d: date) -> str:
    return d.isoformat()


def _fr(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def seed_finance_data(db: Session, org_id: int, *, today: date = TODAY) -> dict:
    """Jeu de données complet et déterministe pour les calculs du moteur.

    - Banque : 1 compte (12 000 €), 5 transactions sur 2 mois
    - Facturation : 4 factures (payée, impayée, en attente, annulée) + 1 devis
    - Fournisseurs : 2 factures (1 à vérifier, TVA déductible 240 €)
    - Synchronisation : 1 connexion fraîche + 2 runs (1 succès, 1 échec)
    """
    prev_month = (today.replace(day=1) - timedelta(days=1)).replace(day=10)

    account = BankAccount(
        organization_id=org_id,
        provider="demo",
        label="Compte pro",
        bank_name="Banque Test",
        balance=12000.0,
        connected=True,
        last_sync_at=datetime.utcnow(),
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    txs = [
        # mois courant : +5 000 / -2 000 (loyer) / -500 (publicité, anomalie)
        BankTransaction(
            account_id=account.id, external_id="t1", booked_at=_iso(today.replace(day=2)),
            label="VIREMENT CLIENT ALPHA", amount=5000.0, category="clients",
        ),
        BankTransaction(
            account_id=account.id, external_id="t2", booked_at=_iso(today.replace(day=5)),
            label="LOYER BUREAUX", amount=-2000.0, category="loyer",
        ),
        BankTransaction(
            account_id=account.id, external_id="t3", booked_at=_iso(today.replace(day=8)),
            label="GOOGLE ADS", amount=-500.0, category="publicite", is_anomaly=True,
            anomaly_reason="Montant inhabituel",
        ),
        # mois précédent : +3 000 / -1 500
        BankTransaction(
            account_id=account.id, external_id="t4", booked_at=_iso(prev_month),
            label="VIREMENT CLIENT BETA", amount=3000.0, category="clients",
        ),
        BankTransaction(
            account_id=account.id, external_id="t5", booked_at=_iso(prev_month),
            label="LOYER BUREAUX", amount=-1500.0, category="loyer",
        ),
    ]
    db.add_all(txs)

    sales = [
        # facture payée du mois courant : CA 10 000 HT, TVA 2 000
        SalesDocument(
            organization_id=org_id, doc_type="facture", number="F-2026-001",
            issue_date=_fr(today.replace(day=3)), due_date=_fr(today.replace(day=28)),
            status="paid", customer_name="Alpha", amount_ht=10000.0, amount_tva=2000.0,
            amount_ttc=12000.0, paid_amount=12000.0,
        ),
        # facture impayée (échéance dépassée) : reste 3 600 TTC
        SalesDocument(
            organization_id=org_id, doc_type="facture", number="F-2026-002",
            issue_date=_fr(prev_month), due_date=_fr(today - timedelta(days=10)),
            status="overdue", customer_name="Beta", amount_ht=3000.0, amount_tva=600.0,
            amount_ttc=3600.0, paid_amount=0.0,
        ),
        # facture en attente (échéance future) : reste 1 200 TTC
        SalesDocument(
            organization_id=org_id, doc_type="facture", number="F-2026-003",
            issue_date=_fr(today.replace(day=10)), due_date=_fr(today + timedelta(days=20)),
            status="sent", customer_name="Gamma", amount_ht=1000.0, amount_tva=200.0,
            amount_ttc=1200.0, paid_amount=0.0,
        ),
        # facture annulée : ignorée du CA
        SalesDocument(
            organization_id=org_id, doc_type="facture", number="F-2026-004",
            issue_date=_fr(today.replace(day=11)), due_date="",
            status="cancelled", customer_name="Delta", amount_ht=9999.0, amount_tva=0.0,
            amount_ttc=9999.0, paid_amount=0.0,
        ),
        # devis : ignoré du CA
        SalesDocument(
            organization_id=org_id, doc_type="devis", number="D-2026-001",
            issue_date=_fr(today.replace(day=12)), due_date="",
            status="sent", customer_name="Epsilon", amount_ht=7777.0, amount_tva=0.0,
            amount_ttc=7777.0, paid_amount=0.0,
        ),
    ]
    db.add_all(sales)

    suppliers = [
        Invoice(
            organization_id=org_id, filename="fournisseur1.pdf", stored_path="/tmp/f1.pdf",
            supplier="Orange", amount_ht=800.0, amount_tva=160.0, amount_ttc=960.0,
            status="done", needs_review=False, invoice_date=_iso(today.replace(day=4)),
        ),
        Invoice(
            organization_id=org_id, filename="fournisseur2.pdf", stored_path="/tmp/f2.pdf",
            supplier="EDF", amount_ht=400.0, amount_tva=80.0, amount_ttc=480.0,
            status="done", needs_review=True, invoice_date=_iso(today.replace(day=6)),
        ),
    ]
    db.add_all(suppliers)

    connection = banking_models.ElfisBankConnection(
        organization_id=org_id, provider="demo", bank_name="Banque Test",
        status="connected", last_sync_at=datetime.utcnow() - timedelta(hours=2),
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    runs = [
        banking_models.ElfisBankSyncRun(
            organization_id=org_id, connection_id=connection.id, provider="demo",
            status="success", started_at=datetime.utcnow() - timedelta(hours=2),
            finished_at=datetime.utcnow() - timedelta(hours=2), duration_ms=1200.0,
        ),
        banking_models.ElfisBankSyncRun(
            organization_id=org_id, connection_id=connection.id, provider="demo",
            status="failed", started_at=datetime.utcnow() - timedelta(days=1),
            error_message="Panne test",
        ),
    ]
    db.add_all(runs)
    db.commit()

    return {"account": account, "connection": connection}
