"""Tests des KPIs standardisés — homogénéité et valeurs."""

from __future__ import annotations

from app.financial.engine import FinancialEngine, build_kpis

from tests.financial.helpers import TODAY, make_financial_db, seed_finance_data, seed_org

EXPECTED_IDS = [
    "tresorerie",
    "revenus",
    "depenses",
    "resultat",
    "tva_estimee",
    "factures_impayees",
    "factures_en_attente",
    "documents_a_traiter",
    "synchronisations_bancaires",
]


def _snap(db, org_id):
    return FinancialEngine(db, use_cache=False, publish_events=False).snapshot(
        org_id, today=TODAY
    )


def test_all_nine_kpis_present_in_order():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    kpis = build_kpis(_snap(db, org.id))
    assert [k.id for k in kpis] == EXPECTED_IDS


def test_kpis_are_homogeneous():
    """Tous les KPI exposent exactement la même structure."""
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    dumps = [k.model_dump() for k in build_kpis(_snap(db, org.id))]
    keys = {frozenset(d.keys()) for d in dumps}
    assert len(keys) == 1
    assert keys.pop() == frozenset(
        {"id", "label", "value", "unit", "format", "status", "trend", "hint"}
    )
    trend_keys = {frozenset(d["trend"].keys()) for d in dumps}
    assert trend_keys.pop() == frozenset({"direction", "delta", "delta_pct", "previous"})


def test_kpi_values_from_engine():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    kpis = {k.id: k for k in build_kpis(_snap(db, org.id))}

    assert kpis["tresorerie"].value == 12000.0
    assert kpis["tresorerie"].status.value == "ok"
    assert kpis["revenus"].value == 14000.0
    assert kpis["depenses"].value == 4000.0
    assert kpis["resultat"].value == 8500.0
    assert kpis["tva_estimee"].value == 2560.0
    assert kpis["factures_impayees"].value == 1
    assert kpis["factures_impayees"].status.value == "warning"
    assert kpis["factures_en_attente"].value == 1
    assert kpis["documents_a_traiter"].value == 1
    assert kpis["synchronisations_bancaires"].value == 1
    assert kpis["synchronisations_bancaires"].status.value == "ok"


def test_kpi_trends_compare_previous_month():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)

    kpis = {k.id: k for k in build_kpis(_snap(db, org.id))}

    # revenus du mois : 11 000 vs 3 000 le mois précédent
    assert kpis["revenus"].trend.direction.value == "up"
    assert kpis["revenus"].trend.previous == 3000.0
    assert kpis["revenus"].trend.delta == 8000.0
    # résultat : 8 500 vs 1 500
    assert kpis["resultat"].trend.delta == 7000.0


def test_kpi_statuses_on_empty_org():
    db = make_financial_db()
    org = seed_org(db)

    kpis = {k.id: k for k in build_kpis(_snap(db, org.id))}

    assert kpis["tresorerie"].status.value == "neutral"  # pas de banque
    assert kpis["factures_impayees"].status.value == "ok"
    assert kpis["synchronisations_bancaires"].status.value == "neutral"


def test_mixed_currencies_kpi_has_no_numeric_total():
    from app.models import BankAccount

    db = make_financial_db()
    org = seed_org(db)
    db.add(BankAccount(organization_id=org.id, currency="EUR", balance=10000.0, connected=True))
    db.add(BankAccount(organization_id=org.id, currency="USD", balance=5000.0, connected=True))
    db.commit()

    kpis = {k.id: k for k in build_kpis(_snap(db, org.id))}
    assert kpis["tresorerie"].value is None
    assert "EUR" in kpis["tresorerie"].hint
    assert "USD" in kpis["tresorerie"].hint
    assert "pas de total unique" in kpis["tresorerie"].hint.lower()


def test_treasury_critical_status():
    db = make_financial_db()
    org = seed_org(db)
    data = seed_finance_data(db, org.id)
    data["account"].balance = 500.0
    db.commit()

    kpis = {k.id: k for k in build_kpis(_snap(db, org.id))}
    assert kpis["tresorerie"].status.value == "critical"
