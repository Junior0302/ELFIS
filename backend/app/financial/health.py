"""Financial Health Score — note de santé financière de 0 à 100.

Barème documenté (et évolutif — chaque composant est indépendant) :

| Composant       | Poids | Règle                                                        |
|-----------------|-------|--------------------------------------------------------------|
| Trésorerie      | 30    | Autonomie = trésorerie / dépenses mensuelles moyennes.       |
|                 |       | ≥ 3 mois : 30 pts, proportionnel en dessous, 0 si négative.  |
| Retards clients | 20    | Ratio impayés / CA. 0 % : 20 pts, ≥ 30 % : 0 pt (linéaire).  |
| Revenus         | 20    | Évolution du CA mensuel. ≥ 0 % : 20 pts, ≤ −50 % : 0 pt.     |
| Dépenses        | 15    | Ratio dépenses / CA. ≤ 70 % : 15 pts, ≥ 120 % : 0 pt.        |
| Synchronisation | 15    | < 24 h : 15 pts, < 7 j : 8 pts, sinon 0. Sans banque : 5 pts.|

Grades : A ≥ 80 · B ≥ 65 · C ≥ 50 · D ≥ 35 · E < 35.
Sans aucune donnée, le score est ``null`` avec l'état ``setup``.
"""

from __future__ import annotations

from app.financial.financial_types import HealthComponent


def _grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "E"


def _linear(value: float, *, worst: float, best: float, max_score: float) -> float:
    """Interpole linéairement value entre worst (0 pt) et best (max)."""
    if best == worst:
        return max_score
    ratio = (value - worst) / (best - worst)
    return round(max(0.0, min(1.0, ratio)) * max_score, 1)


def compute_health_score(snap: dict) -> dict:
    if not snap["has_data"]:
        return {
            "score": None,
            "grade": None,
            "state": "setup",
            "components": [],
            "message": "Ajoutez vos premières données (banque, factures) pour activer le score.",
        }

    components: list[HealthComponent] = []

    # 1. Trésorerie (30) — autonomie en mois de dépenses
    monthly = snap["monthly"]
    keys = snap["month_keys"]
    monthly_expenses = [monthly.get(k, {}).get("expenses", 0.0) for k in keys]
    active_months = [e for e in monthly_expenses if e > 0]
    avg_expenses = (sum(active_months) / len(active_months)) if active_months else 0.0
    if snap["treasury"] <= 0:
        treasury_score = 0.0
        treasury_detail = "Trésorerie négative ou nulle."
    elif avg_expenses <= 0:
        treasury_score = 30.0 if snap["treasury"] > 0 else 0.0
        treasury_detail = "Pas de dépenses récurrentes détectées."
    else:
        runway = snap["treasury"] / avg_expenses
        treasury_score = _linear(runway, worst=0.0, best=3.0, max_score=30.0)
        treasury_detail = f"Autonomie estimée : {runway:.1f} mois de dépenses."
    components.append(
        HealthComponent(id="treasury", label="Trésorerie", score=treasury_score, max_score=30.0, detail=treasury_detail)
    )

    # 2. Retards clients (20) — impayés / CA
    if snap["revenue"] > 0:
        overdue_ratio = snap["overdue_amount"] / snap["revenue"]
        overdue_score = _linear(overdue_ratio, worst=0.30, best=0.0, max_score=20.0)
        overdue_detail = f"Impayés = {overdue_ratio * 100:.1f}% du CA."
    else:
        overdue_score = 20.0 if not snap["overdue_count"] else 0.0
        overdue_detail = "Pas de chiffre d'affaires facturé."
    components.append(
        HealthComponent(id="overdue", label="Retards clients", score=overdue_score, max_score=20.0, detail=overdue_detail)
    )

    # 3. Revenus (20) — dynamique du CA mensuel
    cur_rev = monthly.get(keys[-1], {}).get("revenue", 0.0)
    prev_rev = monthly.get(keys[-2], {}).get("revenue", 0.0) if len(keys) > 1 else 0.0
    if prev_rev > 0:
        growth_pct = ((cur_rev - prev_rev) / prev_rev) * 100
        revenue_score = _linear(growth_pct, worst=-50.0, best=0.0, max_score=20.0)
        revenue_detail = f"Évolution du CA mensuel : {growth_pct:+.1f}%."
    else:
        revenue_score = 20.0 if cur_rev > 0 else 10.0
        revenue_detail = "Historique de CA insuffisant pour mesurer la dynamique."
    components.append(
        HealthComponent(id="revenue", label="Revenus", score=revenue_score, max_score=20.0, detail=revenue_detail)
    )

    # 4. Dépenses (15) — dépenses / CA
    if snap["revenue"] > 0:
        expense_ratio = (snap["expenses"] / snap["revenue"]) * 100
        expense_score = _linear(expense_ratio, worst=120.0, best=70.0, max_score=15.0)
        expense_detail = f"Dépenses = {expense_ratio:.0f}% du CA."
    else:
        expense_score = 7.5 if snap["expenses"] else 15.0
        expense_detail = "Ratio dépenses/CA non mesurable sans CA."
    components.append(
        HealthComponent(id="expenses", label="Dépenses", score=expense_score, max_score=15.0, detail=expense_detail)
    )

    # 5. Synchronisation bancaire (15)
    sync = snap["sync"]
    if sync["status"] == "fresh":
        sync_score, sync_detail = 15.0, "Données bancaires synchronisées (moins de 24 h)."
    elif sync["status"] == "aging":
        sync_score, sync_detail = 8.0, "Dernière synchronisation il y a plus de 24 h."
    elif sync["status"] in {"stale", "error"}:
        sync_score, sync_detail = 0.0, "Synchronisation bancaire absente ou en erreur."
    else:  # none
        sync_score, sync_detail = 5.0, "Aucune banque connectée."
    components.append(
        HealthComponent(id="sync", label="Synchronisation", score=sync_score, max_score=15.0, detail=sync_detail)
    )

    score = round(sum(c.score for c in components), 1)
    return {
        "score": score,
        "grade": _grade(score),
        "state": "active",
        "components": [c.model_dump() for c in components],
        "message": None,
    }
