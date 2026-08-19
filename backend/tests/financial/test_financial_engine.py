"""Tests des calculs du Financial Engine (snapshot = source de vérité)."""

from __future__ import annotations

from app.financial.engine import FinancialEngine

from tests.financial.helpers import TODAY, make_financial_db, seed_finance_data, seed_org


def _engine(db) -> FinancialEngine:
    return FinancialEngine(db, use_cache=False, publish_events=False)


def test_snapshot_core_aggregates():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    snap = _engine(db).snapshot(org.id, today=TODAY)

    assert snap["treasury"] == 12000.0
    assert snap["credits"] == 8000.0
    assert snap["expenses"] == 4000.0
    assert snap["revenue"] == 14000.0  # annulée et devis exclus
    assert snap["vat_collected"] == 2800.0
    assert snap["vat_deductible"] == 240.0
    assert snap["vat_estimated"] == 2560.0
    assert snap["profit"] == 10000.0
    assert snap["margin_pct"] == 71.4
    assert snap["has_data"] is True


def test_snapshot_invoices_and_documents():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    snap = _engine(db).snapshot(org.id, today=TODAY)

    assert snap["overdue_count"] == 1
    assert snap["overdue_amount"] == 3600.0
    assert snap["pending_count"] == 1
    assert snap["pending_amount"] == 1200.0
    assert snap["unpaid_amount"] == 4800.0
    assert snap["documents_to_process"] == 1
    assert snap["anomalies"] == 1


def test_snapshot_monthly_buckets_and_result():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    snap = _engine(db).snapshot(org.id, today=TODAY)
    current = snap["monthly"][snap["month_keys"][-1]]
    previous = snap["monthly"][snap["month_keys"][-2]]

    assert current["revenue"] == 11000.0  # F-001 (10 000) + F-003 (1 000)
    assert current["expenses"] == 2500.0
    assert previous["revenue"] == 3000.0
    assert previous["expenses"] == 1500.0
    assert snap["month_result"] == 8500.0


def test_treasury_series_reconstructs_balance():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    snap = _engine(db).snapshot(org.id, today=TODAY)
    series = snap["treasury_series"]

    assert series[-1]["value"] == 12000.0  # dernier point = solde actuel
    # avant le mois courant (net +2 500), le solde reconstitué était 9 500
    assert series[-2]["value"] == 9500.0


def test_snapshot_sync_state():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    snap = _engine(db).snapshot(org.id, today=TODAY)
    sync = snap["sync"]

    assert sync["connections"] == 1
    assert sync["status"] == "fresh"
    assert sync["ok_runs_7d"] == 1
    assert sync["failed_runs_7d"] == 1


def test_snapshot_isolated_by_organization():
    db = make_financial_db()
    org_a = seed_org(db, "Org A")
    org_b = seed_org(db, "Org B")
    seed_finance_data(db, org_a.id)

    snap_b = _engine(db).snapshot(org_b.id, today=TODAY)

    assert snap_b["treasury"] == 0.0
    assert snap_b["revenue"] == 0.0
    assert snap_b["has_data"] is False


def test_empty_organization_snapshot_is_safe():
    db = make_financial_db()
    org = seed_org(db)

    snap = _engine(db).snapshot(org.id, today=TODAY)

    assert snap["treasury"] == 0.0
    assert snap["margin_pct"] == 0.0
    assert snap["forecast"] == {"30": 0.0, "60": 0.0, "90": 0.0}
    assert snap["sync"]["status"] == "none"


def test_forecast_positive_flow_no_tensions():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    snap = _engine(db).snapshot(org.id, today=TODAY)

    # net période = +4 000 → daily ≈ 266,67 → J+30 = 12 000 + 8 000
    assert snap["forecast"]["30"] == 20000.0
    assert snap["tensions"] == []
    assert any("saine" in r for r in snap["recommendations"])


def test_snapshot_compat_matches_legacy_contract():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    compat = FinancialEngine(db, use_cache=False, publish_events=False).snapshot_compat(org.id)

    expected_keys = {
        "balance", "credits", "debits", "duplicates", "anomalies", "to_reconcile",
        "forecast", "tensions", "recommendations", "supplier_ht", "supplier_vat",
        "to_review", "ca", "unpaid", "overdue_clients", "charges", "marge",
        "marge_pct", "top_charge", "has_data",
    }
    assert set(compat.keys()) == expected_keys
    assert compat["balance"] == 12000.0
    assert compat["ca"] == 14000.0
    assert compat["charges"] == 4000.0
    assert compat["marge"] == 10000.0
    assert compat["supplier_vat"] == 240.0
    assert compat["top_charge"]["category"] == "loyer"
    assert compat["top_charge"]["amount"] == 3500.0


def test_finance_agent_delegates_to_engine():
    """Le chat Finance Agent consomme la même source de vérité."""
    from app.services.finance_agent import _finance_snapshot

    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    snap = _finance_snapshot(db, org.id)
    assert snap["ca"] == 14000.0
    assert snap["balance"] == 12000.0
