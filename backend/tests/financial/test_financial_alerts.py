"""Tests du moteur d'alertes normalisées."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.financial.alerts import build_alerts
from app.financial.engine import FinancialEngine

from tests.financial.helpers import TODAY, make_financial_db, seed_finance_data, seed_org


def _alerts(db, org_id):
    snap = FinancialEngine(db, use_cache=False, publish_events=False).snapshot(
        org_id, today=TODAY
    )
    return build_alerts(snap)


def test_nominal_dataset_raises_expected_alerts():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    codes = {a.code for a in _alerts(db, org.id)}
    assert "INVOICE_OVERDUE" in codes
    assert "UNUSUAL_EXPENSE" in codes
    assert "DOCUMENTS_PENDING" in codes
    assert "TREASURY_LOW" not in codes  # 12 000 € > seuil
    assert "SYNC_MISSING" not in codes  # sync fraîche


def test_alerts_are_normalized():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    for alert in _alerts(db, org.id):
        dump = alert.model_dump()
        assert set(dump.keys()) == {
            "id", "code", "severity", "title", "message", "action", "source",
            "value", "created_at",
        }
        assert dump["severity"] in {"info", "warning", "critical"}
        assert dump["title"] and dump["message"]


def test_treasury_low_and_critical_alerts():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)

    data["account"].balance = 3000.0
    db.commit()
    codes = {a.code: a for a in _alerts(db, org.id)}
    assert codes["TREASURY_LOW"].severity.value == "warning"

    data["account"].balance = 400.0
    db.commit()
    codes = {a.code: a for a in _alerts(db, org.id)}
    assert codes["TREASURY_CRITICAL"].severity.value == "critical"
    assert "TREASURY_LOW" not in codes


def test_vat_high_alert():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    from app.models_saas import SalesDocument

    db.add(
        SalesDocument(
            organization_id=org.id, doc_type="facture", number="F-2026-099",
            issue_date=TODAY.strftime("%d-%m-%Y"), status="paid", customer_name="Zeta",
            amount_ht=30000.0, amount_tva=6000.0, amount_ttc=36000.0, paid_amount=36000.0,
        )
    )
    db.commit()

    codes = {a.code for a in _alerts(db, org.id)}
    assert "VAT_HIGH" in codes


def test_overdue_critical_above_10k():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    from app.models_saas import SalesDocument

    db.add(
        SalesDocument(
            organization_id=org.id, doc_type="facture", number="F-2026-098",
            issue_date=TODAY.strftime("%d-%m-%Y"),
            due_date=(TODAY - timedelta(days=30)).strftime("%d-%m-%Y"),
            status="overdue", customer_name="Grosse Dette",
            amount_ht=15000.0, amount_tva=3000.0, amount_ttc=18000.0, paid_amount=0.0,
        )
    )
    db.commit()

    alerts = {a.code: a for a in _alerts(db, org.id)}
    assert alerts["INVOICE_OVERDUE"].severity.value == "critical"


def test_sync_missing_alert_when_stale():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)

    data["connection"].last_sync_at = datetime.utcnow() - timedelta(days=10)
    db.commit()

    codes = {a.code for a in _alerts(db, org.id)}
    assert "SYNC_MISSING" in codes


def test_sync_error_alert():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)

    data["connection"].status = "error"
    db.commit()

    alerts = {a.code: a for a in _alerts(db, org.id)}
    assert alerts["SYNC_ERROR"].severity.value == "critical"


def test_alerts_sorted_by_severity():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)
    data["account"].balance = 400.0  # critique
    db.commit()

    alerts = _alerts(db, org.id)
    order = {"critical": 0, "warning": 1, "info": 2}
    ranks = [order[a.severity.value] for a in alerts]
    assert ranks == sorted(ranks)
    assert alerts[0].severity.value == "critical"


def test_mixed_currencies_do_not_raise_treasury_alerts():
    from app.models import BankAccount

    db = make_financial_db()
    org = seed_org(db)
    db.add(BankAccount(organization_id=org.id, currency="EUR", balance=100.0, connected=True))
    db.add(BankAccount(organization_id=org.id, currency="USD", balance=200.0, connected=True))
    db.commit()

    codes = {a.code for a in _alerts(db, org.id)}
    assert "TREASURY_LOW" not in codes
    assert "TREASURY_CRITICAL" not in codes


def test_no_alerts_on_empty_org_except_none():
    db = make_financial_db()
    org = seed_org(db)

    alerts = _alerts(db, org.id)
    assert alerts == []  # has_data False → même pas SYNC_NOT_CONFIGURED
