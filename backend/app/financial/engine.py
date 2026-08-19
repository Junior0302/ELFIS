"""Financial Engine — unique source de vérité des indicateurs financiers.

Le moteur agrège les données Banking (comptes, transactions, synchronisations),
Facturation (SalesDocument) et Fournisseurs (Invoice) en un *snapshot* brut,
mis en cache par organisation (TTL configurable). Tous les KPIs, tendances,
séries de graphiques, alertes et le Health Score dérivent de ce snapshot :
aucun calcul n'est effectué dans le frontend ni dupliqué ailleurs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.banking.banking_models import ElfisBankConnection, ElfisBankSyncRun
from app.financial import financial_events
from app.financial.alerts import build_alerts
from app.financial.cache import snapshot_cache, value_changed
from app.financial.financial_types import (
    Kpi,
    KpiStatus,
    KpiTrend,
    TrendDirection,
    TrendPoint,
    parse_flexible_date,
)
from app.financial.health import compute_health_score
from app.models import BankAccount, BankTransaction, Invoice
from app.models_saas import SalesDocument

MONTHS_WINDOW = 12
WEEKS_WINDOW = 12
YEARS_WINDOW = 3

_UNPAID_STATUSES = {"sent", "partial", "overdue", "accepted"}


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]:04d}-S{iso[1]:02d}"


def _year_key(d: date) -> str:
    return f"{d.year:04d}"


def _shift_month(d: date, delta: int) -> date:
    month = d.month - 1 + delta
    year = d.year + month // 12
    return date(year, month % 12 + 1, 1)


def _trend(current: float, previous: float) -> KpiTrend:
    delta = round(current - previous, 2)
    if abs(delta) < 0.005:
        direction = TrendDirection.flat
    elif delta > 0:
        direction = TrendDirection.up
    else:
        direction = TrendDirection.down
    delta_pct = round((delta / abs(previous)) * 100, 1) if previous else None
    return KpiTrend(direction=direction, delta=delta, delta_pct=delta_pct, previous=round(previous, 2))


class FinancialEngine:
    """Moteur central de calcul financier (source de vérité unique)."""

    def __init__(self, db: Session, *, use_cache: bool = True, publish_events: bool = True):
        self.db = db
        self.use_cache = use_cache
        self.publish_events = publish_events

    # ------------------------------------------------------------------
    # Snapshot (agrégats bruts, cachés par organisation)
    # ------------------------------------------------------------------

    def snapshot(self, organization_id: int, *, refresh: bool = False, today: date | None = None) -> dict:
        if self.use_cache and not refresh:
            cached = snapshot_cache.get(organization_id)
            if cached is not None:
                return cached
        snap = self._compute_snapshot(organization_id, today=today or date.today())
        if self.use_cache:
            snapshot_cache.set(organization_id, snap)
        if self.publish_events:
            self._publish_updates(organization_id, snap)
        return snap

    def invalidate(self, organization_id: int) -> None:
        snapshot_cache.invalidate(organization_id)

    def _compute_snapshot(self, organization_id: int, *, today: date) -> dict:
        accounts = (
            self.db.query(BankAccount)
            .filter(BankAccount.organization_id == organization_id)
            .all()
        )
        account_ids = [a.id for a in accounts]
        txs: list[BankTransaction] = []
        if account_ids:
            txs = (
                self.db.query(BankTransaction)
                .filter(BankTransaction.account_id.in_(account_ids))
                .all()
            )

        treasury = round(sum(float(a.balance) for a in accounts), 2)
        credits = round(sum(t.amount for t in txs if t.amount > 0), 2)
        debits = round(sum(t.amount for t in txs if t.amount < 0), 2)
        expenses = round(abs(debits), 2)
        duplicates = sum(1 for t in txs if t.is_duplicate)
        anomalies = sum(1 for t in txs if t.is_anomaly or t.is_duplicate)
        to_reconcile = sum(1 for t in txs if not t.reconciled and t.amount < 0)

        expense_by_category: dict[str, dict] = {}
        for t in txs:
            if t.amount >= 0:
                continue
            cat = t.category or "autre"
            entry = expense_by_category.setdefault(cat, {"amount": 0.0, "count": 0})
            entry["amount"] = round(entry["amount"] + abs(t.amount), 2)
            entry["count"] += 1

        # --- Facturation clients (CA, impayés, en attente, TVA collectée) ---
        sales = (
            self.db.query(SalesDocument)
            .filter(SalesDocument.organization_id == organization_id)
            .all()
        )
        invoices_sales = [d for d in sales if d.doc_type == "facture" and d.status != "cancelled"]
        revenue = round(sum(d.amount_ht for d in invoices_sales), 2)
        vat_collected = round(sum(d.amount_tva for d in invoices_sales), 2)

        overdue_amount = 0.0
        overdue_count = 0
        pending_amount = 0.0
        pending_count = 0
        unpaid_amount = 0.0
        overdue_customers: set[str] = set()
        for d in invoices_sales:
            remaining = max(0.0, d.amount_ttc - d.paid_amount)
            if remaining <= 0 or d.status not in _UNPAID_STATUSES:
                continue
            unpaid_amount += remaining
            due = parse_flexible_date(d.due_date)
            is_overdue = d.status == "overdue" or (due is not None and due < today)
            if is_overdue:
                overdue_amount += remaining
                overdue_count += 1
                overdue_customers.add(d.customer_name)
            else:
                pending_amount += remaining
                pending_count += 1

        # --- Factures fournisseurs (TVA déductible, documents à traiter) ---
        supplier_q = self.db.query(Invoice).filter(Invoice.organization_id == organization_id)
        suppliers = supplier_q.all()
        supplier_ht = round(sum(float(i.amount_ht or 0.0) for i in suppliers), 2)
        vat_deductible = round(sum(float(i.amount_tva or 0.0) for i in suppliers), 2)
        to_review = sum(1 for i in suppliers if i.needs_review)
        processing = sum(1 for i in suppliers if i.status == "processing")
        documents_to_process = to_review + processing

        vat_estimated = round(vat_collected - vat_deductible, 2)
        profit = round(revenue - expenses, 2)
        margin_pct = round((profit / revenue) * 100, 1) if revenue else 0.0

        # --- Buckets temporels (tendances / graphiques) ---
        monthly = self._buckets(invoices_sales, txs, key=_month_key)
        weekly = self._buckets(invoices_sales, txs, key=_week_key)
        yearly = self._buckets(invoices_sales, txs, key=_year_key)

        month_keys = [_month_key(_shift_month(today, -i)) for i in range(MONTHS_WINDOW - 1, -1, -1)]
        week_keys = [_week_key(today - timedelta(weeks=i)) for i in range(WEEKS_WINDOW - 1, -1, -1)]
        year_keys = [str(today.year - i) for i in range(YEARS_WINDOW - 1, -1, -1)]

        current_month = monthly.get(month_keys[-1], {"revenue": 0.0, "expenses": 0.0})
        month_result = round(current_month["revenue"] - current_month["expenses"], 2)

        # --- Série de trésorerie (solde reconstitué mois par mois) ---
        net_by_month: dict[str, float] = {}
        for t in txs:
            d = parse_flexible_date(t.booked_at)
            if d is None:
                continue
            k = _month_key(d)
            net_by_month[k] = round(net_by_month.get(k, 0.0) + t.amount, 2)
        treasury_series: list[dict] = []
        running = treasury
        for k in reversed(month_keys):
            treasury_series.append({"period": k, "value": round(running, 2)})
            running -= net_by_month.get(k, 0.0)
        treasury_series.reverse()

        # --- Prévision de trésorerie 30/60/90 j (formule historique conservée) ---
        forecast, tensions, recommendations = self._forecast(
            treasury, txs, has_account=bool(accounts)
        )

        # --- Synchronisations bancaires ---
        sync = self._sync_state(organization_id)

        has_data = bool(accounts or sales or supplier_ht or to_review)

        return {
            "organization_id": organization_id,
            "computed_at": datetime.utcnow().isoformat(),
            "today": today.isoformat(),
            "treasury": treasury,
            "accounts_count": len(accounts),
            "has_bank": bool(accounts),
            "tx_count": len(txs),
            "credits": credits,
            "debits": debits,
            "expenses": expenses,
            "duplicates": duplicates,
            "anomalies": anomalies,
            "to_reconcile": to_reconcile,
            "expense_by_category": expense_by_category,
            "revenue": revenue,
            "vat_collected": vat_collected,
            "vat_deductible": vat_deductible,
            "vat_estimated": vat_estimated,
            "supplier_ht": supplier_ht,
            "unpaid_amount": round(unpaid_amount, 2),
            "overdue_amount": round(overdue_amount, 2),
            "overdue_count": overdue_count,
            "overdue_clients": len(overdue_customers),
            "pending_amount": round(pending_amount, 2),
            "pending_count": pending_count,
            "to_review": to_review,
            "documents_to_process": documents_to_process,
            "profit": profit,
            "margin_pct": margin_pct,
            "month_result": month_result,
            "monthly": monthly,
            "weekly": weekly,
            "yearly": yearly,
            "month_keys": month_keys,
            "week_keys": week_keys,
            "year_keys": year_keys,
            "treasury_series": treasury_series,
            "forecast": forecast,
            "tensions": tensions,
            "recommendations": recommendations,
            "sync": sync,
            "has_data": has_data,
        }

    @staticmethod
    def _buckets(sales: list[SalesDocument], txs: list[BankTransaction], *, key) -> dict[str, dict]:
        buckets: dict[str, dict] = {}

        def entry(k: str) -> dict:
            return buckets.setdefault(k, {"revenue": 0.0, "expenses": 0.0})

        for d in sales:
            issued = parse_flexible_date(d.issue_date)
            if issued is None:
                continue
            e = entry(key(issued))
            e["revenue"] = round(e["revenue"] + d.amount_ht, 2)
        for t in txs:
            if t.amount >= 0:
                continue
            booked = parse_flexible_date(t.booked_at)
            if booked is None:
                continue
            e = entry(key(booked))
            e["expenses"] = round(e["expenses"] + abs(t.amount), 2)
        return buckets

    @staticmethod
    def _forecast(
        treasury: float, txs: list[BankTransaction], *, has_account: bool
    ) -> tuple[dict, list[str], list[str]]:
        if not has_account:
            return (
                {"30": 0.0, "60": 0.0, "90": 0.0},
                [],
                ["Connectez votre banque pour projeter la trésorerie sur 30 / 60 / 90 jours."],
            )
        net = sum(t.amount for t in txs) if txs else 0.0
        daily = (net / 15.0) if txs else 0.0
        day30 = round(treasury + daily * 30, 2)
        day60 = round(treasury + daily * 60, 2)
        day90 = round(treasury + daily * 90, 2)

        tensions: list[str] = []
        recommendations: list[str] = []
        if not txs:
            recommendations.append(
                "Aucune opération importée. Synchronisez vos mouvements bancaires pour activer les alertes."
            )
        else:
            if day30 < 5000:
                tensions.append("Tension de trésorerie probable sous 30 jours.")
                recommendations.append(
                    "Reporter les investissements non urgents et relancer les clients en retard."
                )
            if day60 < 3000:
                tensions.append("Solde critique envisageable à 60 jours.")
                recommendations.append(
                    "Négocier un délai fournisseur ou une ligne de crédit de trésorerie."
                )
            if abs(daily) > 200 and daily < 0:
                tensions.append("Le rythme de décaissement dépasse les encaissements.")
                recommendations.append(
                    "Revoir les abonnements et plafonner les dépenses publicitaires."
                )
            if not tensions:
                recommendations.append(
                    "Trésorerie saine à court terme — maintenir le suivi hebdomadaire."
                )
        return {"30": day30, "60": day60, "90": day90}, tensions, recommendations

    def _sync_state(self, organization_id: int) -> dict:
        connections = (
            self.db.query(ElfisBankConnection)
            .filter(ElfisBankConnection.organization_id == organization_id)
            .all()
        )
        active = [c for c in connections if c.status not in {"disconnected"}]
        errors = sum(1 for c in connections if c.status == "error")
        last_sync = None
        for c in active:
            if c.last_sync_at and (last_sync is None or c.last_sync_at > last_sync):
                last_sync = c.last_sync_at

        since = datetime.utcnow() - timedelta(days=7)
        runs = (
            self.db.query(ElfisBankSyncRun)
            .filter(
                ElfisBankSyncRun.organization_id == organization_id,
                ElfisBankSyncRun.started_at >= since,
            )
            .all()
        )
        failed_7d = sum(1 for r in runs if r.status == "failed")
        ok_7d = sum(1 for r in runs if r.status == "success")

        age_hours: float | None = None
        if last_sync is not None:
            age_hours = round((datetime.utcnow() - last_sync).total_seconds() / 3600.0, 1)

        if not active:
            status = "none"
        elif errors:
            status = "error"
        elif age_hours is None or age_hours > 24 * 7:
            status = "stale"
        elif age_hours > 24:
            status = "aging"
        else:
            status = "fresh"

        return {
            "connections": len(active),
            "errors": errors,
            "last_sync_at": last_sync.isoformat() if last_sync else None,
            "age_hours": age_hours,
            "failed_runs_7d": failed_7d,
            "ok_runs_7d": ok_7d,
            "status": status,
        }

    # ------------------------------------------------------------------
    # KPIs standardisés
    # ------------------------------------------------------------------

    def kpis(self, organization_id: int, *, refresh: bool = False) -> list[Kpi]:
        snap = self.snapshot(organization_id, refresh=refresh)
        return build_kpis(snap)

    # ------------------------------------------------------------------
    # Tendances (mensuelle / hebdomadaire / annuelle + comparaisons)
    # ------------------------------------------------------------------

    def trends(self, organization_id: int, *, refresh: bool = False) -> dict:
        snap = self.snapshot(organization_id, refresh=refresh)
        return {
            "monthly": self._trend_block(snap["monthly"], snap["month_keys"]),
            "weekly": self._trend_block(snap["weekly"], snap["week_keys"]),
            "yearly": self._trend_block(snap["yearly"], snap["year_keys"]),
        }

    @staticmethod
    def _trend_block(buckets: dict[str, dict], keys: list[str]) -> dict:
        points: list[TrendPoint] = []
        for k in keys:
            b = buckets.get(k, {"revenue": 0.0, "expenses": 0.0})
            points.append(
                TrendPoint(
                    period=k,
                    label=k,
                    revenue=b["revenue"],
                    expenses=b["expenses"],
                    result=round(b["revenue"] - b["expenses"], 2),
                )
            )
        current = points[-1] if points else TrendPoint(period="", label="")
        previous = points[-2] if len(points) > 1 else TrendPoint(period="", label="")
        return {
            "points": [p.model_dump() for p in points],
            "comparison": {
                "revenue": _trend(current.revenue, previous.revenue).model_dump(),
                "expenses": _trend(current.expenses, previous.expenses).model_dump(),
                "result": _trend(current.result, previous.result).model_dump(),
            },
        }

    # ------------------------------------------------------------------
    # Séries pour graphiques (le frontend ne fait qu'afficher)
    # ------------------------------------------------------------------

    def charts(self, organization_id: int, *, refresh: bool = False) -> dict:
        snap = self.snapshot(organization_id, refresh=refresh)
        monthly = snap["monthly"]
        keys = snap["month_keys"]

        revenue_vs_expenses = [
            {
                "period": k,
                "revenue": monthly.get(k, {}).get("revenue", 0.0),
                "expenses": monthly.get(k, {}).get("expenses", 0.0),
            }
            for k in keys
        ]
        total_exp = sum(e["amount"] for e in snap["expense_by_category"].values()) or 0.0
        breakdown = sorted(
            (
                {
                    "category": cat,
                    "amount": entry["amount"],
                    "count": entry["count"],
                    "pct": round((entry["amount"] / total_exp) * 100, 1) if total_exp else 0.0,
                }
                for cat, entry in snap["expense_by_category"].items()
            ),
            key=lambda item: -item["amount"],
        )
        ca_evolution = [
            {"period": k, "value": monthly.get(k, {}).get("revenue", 0.0)} for k in keys
        ]
        return {
            "revenue_vs_expenses": revenue_vs_expenses,
            "treasury": snap["treasury_series"],
            "expense_breakdown": breakdown,
            "categories": breakdown,
            "ca_evolution": ca_evolution,
        }

    # ------------------------------------------------------------------
    # Activité récente
    # ------------------------------------------------------------------

    def recent_activity(self, organization_id: int, *, limit: int = 8) -> list[dict]:
        items: list[dict] = []
        accounts = (
            self.db.query(BankAccount.id)
            .filter(BankAccount.organization_id == organization_id)
            .all()
        )
        account_ids = [a[0] for a in accounts]
        if account_ids:
            for t in (
                self.db.query(BankTransaction)
                .filter(BankTransaction.account_id.in_(account_ids))
                .order_by(BankTransaction.id.desc())
                .limit(limit)
                .all()
            ):
                items.append(
                    {
                        "type": "transaction",
                        "label": t.label,
                        "amount": t.amount,
                        "date": t.booked_at,
                        "meta": t.category,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                    }
                )
        for d in (
            self.db.query(SalesDocument)
            .filter(SalesDocument.organization_id == organization_id)
            .order_by(SalesDocument.id.desc())
            .limit(limit)
            .all()
        ):
            items.append(
                {
                    "type": "facture" if d.doc_type == "facture" else d.doc_type,
                    "label": f"{d.number} — {d.customer_name}".strip(" —"),
                    "amount": d.amount_ttc,
                    "date": d.issue_date,
                    "meta": d.status,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
            )
        for i in (
            self.db.query(Invoice)
            .filter(Invoice.organization_id == organization_id)
            .order_by(Invoice.id.desc())
            .limit(limit)
            .all()
        ):
            items.append(
                {
                    "type": "document",
                    "label": i.supplier or i.filename,
                    "amount": float(i.amount_ttc or 0.0),
                    "date": i.invoice_date or "",
                    "meta": i.status,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
            )
        items.sort(key=lambda x: x["created_at"] or "", reverse=True)
        return items[:limit]

    # ------------------------------------------------------------------
    # Vue d'ensemble (tout le dashboard en un appel)
    # ------------------------------------------------------------------

    def overview(self, organization_id: int, *, refresh: bool = False) -> dict:
        snap = self.snapshot(organization_id, refresh=refresh)
        kpis = build_kpis(snap)
        alerts = build_alerts(snap)
        health = compute_health_score(snap)
        return {
            "computed_at": snap["computed_at"],
            "has_data": snap["has_data"],
            "kpis": [k.model_dump() for k in kpis],
            "alerts": [a.model_dump() for a in alerts],
            "health": health,
            "charts": self.charts(organization_id),
            "trends": self.trends(organization_id),
            "sync": snap["sync"],
            "documents_to_process": snap["documents_to_process"],
            "recent_activity": self.recent_activity(organization_id),
            "recommendations": snap["recommendations"][:3],
        }

    # ------------------------------------------------------------------
    # Compatibilité finance_agent (le chat consomme la même vérité)
    # ------------------------------------------------------------------

    def snapshot_compat(self, organization_id: int | None) -> dict:
        """Instantané au format historique de ``_finance_snapshot`` (finance_agent)."""
        snap = self.snapshot(int(organization_id or 0))
        by_cat = {cat: e["amount"] for cat, e in snap["expense_by_category"].items()}
        top = max(by_cat.items(), key=lambda x: x[1]) if by_cat else ("autre", 0.0)
        marge = round(snap["revenue"] - snap["expenses"], 2) if snap["revenue"] or snap["expenses"] else 0.0
        return {
            "balance": snap["treasury"],
            "credits": snap["credits"],
            "debits": snap["debits"],
            "duplicates": snap["duplicates"],
            "anomalies": snap["anomalies"],
            "to_reconcile": snap["to_reconcile"],
            "forecast": snap["forecast"],
            "tensions": snap["tensions"],
            "recommendations": snap["recommendations"],
            "supplier_ht": snap["supplier_ht"],
            "supplier_vat": snap["vat_deductible"],
            "to_review": snap["to_review"],
            "ca": snap["revenue"],
            "unpaid": snap["unpaid_amount"],
            "overdue_clients": snap["overdue_clients"],
            "charges": snap["expenses"],
            "marge": marge,
            "marge_pct": snap["margin_pct"],
            "top_charge": {"category": top[0], "amount": round(top[1], 2)},
            "has_data": snap["has_data"],
        }

    # ------------------------------------------------------------------
    # Événements IA (publication sur changement uniquement)
    # ------------------------------------------------------------------

    def _publish_updates(self, organization_id: int, snap: dict) -> None:
        try:
            kpis = [k.model_dump() for k in build_kpis(snap)]
            kpi_fp = _fingerprint(kpis)
            if value_changed(f"kpis-{organization_id}", kpi_fp):
                financial_events.publish_kpis_updated(
                    self.db, organization_id=organization_id, kpis=kpis, fingerprint=kpi_fp
                )
            health = compute_health_score(snap)
            health_fp = _fingerprint({"score": health["score"], "grade": health["grade"]})
            if value_changed(f"health-{organization_id}", health_fp):
                financial_events.publish_health_updated(
                    self.db,
                    organization_id=organization_id,
                    score=health["score"],
                    grade=health["grade"],
                    components=health["components"],
                    fingerprint=health_fp,
                )
            for alert in build_alerts(snap):
                if value_changed(f"alert-{organization_id}-{alert.code}", alert.severity.value):
                    financial_events.publish_alert_created(
                        self.db, organization_id=organization_id, alert=alert
                    )
        except Exception:
            # la publication d'événements ne doit jamais bloquer les calculs
            pass


def _fingerprint(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


# ----------------------------------------------------------------------
# KPIs standardisés (format homogène — voir financial_types.Kpi)
# ----------------------------------------------------------------------


def build_kpis(snap: dict) -> list[Kpi]:
    monthly = snap["monthly"]
    keys = snap["month_keys"]
    cur = monthly.get(keys[-1], {"revenue": 0.0, "expenses": 0.0})
    prev = monthly.get(keys[-2], {"revenue": 0.0, "expenses": 0.0}) if len(keys) > 1 else cur
    series = snap["treasury_series"]
    treasury_prev = series[-2]["value"] if len(series) > 1 else snap["treasury"]

    treasury_status = KpiStatus.neutral
    if snap["has_bank"]:
        if snap["treasury"] < 1000:
            treasury_status = KpiStatus.critical
        elif snap["treasury"] < 5000:
            treasury_status = KpiStatus.warning
        else:
            treasury_status = KpiStatus.ok

    month_result_prev = round(prev["revenue"] - prev["expenses"], 2)

    sync = snap["sync"]
    sync_status = {
        "fresh": KpiStatus.ok,
        "aging": KpiStatus.warning,
        "stale": KpiStatus.critical,
        "error": KpiStatus.critical,
        "none": KpiStatus.neutral,
    }[sync["status"]]
    sync_hint = "Aucune connexion bancaire"
    if sync["connections"]:
        if sync["age_hours"] is not None:
            sync_hint = f"Dernière synchronisation il y a {sync['age_hours']:.0f} h"
        else:
            sync_hint = "Jamais synchronisé"
        if sync["errors"]:
            sync_hint += f" · {sync['errors']} connexion(s) en erreur"

    return [
        Kpi(
            id="tresorerie",
            label="Trésorerie",
            value=snap["treasury"],
            unit="EUR",
            format="currency",
            status=treasury_status,
            trend=_trend(snap["treasury"], treasury_prev),
            hint=f"Projection 30 j : {snap['forecast']['30']:.0f} €",
        ),
        Kpi(
            id="revenus",
            label="Revenus",
            value=snap["revenue"],
            unit="EUR",
            format="currency",
            status=KpiStatus.ok if snap["revenue"] > 0 else KpiStatus.neutral,
            trend=_trend(cur["revenue"], prev["revenue"]),
            hint="CA facturé HT (factures non annulées)",
        ),
        Kpi(
            id="depenses",
            label="Dépenses",
            value=snap["expenses"],
            unit="EUR",
            format="currency",
            status=KpiStatus.neutral,
            trend=_trend(cur["expenses"], prev["expenses"]),
            hint="Décaissements bancaires cumulés",
        ),
        Kpi(
            id="resultat",
            label="Résultat",
            value=snap["month_result"],
            unit="EUR",
            format="currency",
            status=KpiStatus.ok if snap["month_result"] >= 0 else KpiStatus.warning,
            trend=_trend(snap["month_result"], month_result_prev),
            hint=f"Résultat du mois en cours · marge globale {snap['margin_pct']}%",
        ),
        Kpi(
            id="tva_estimee",
            label="TVA estimée",
            value=snap["vat_estimated"],
            unit="EUR",
            format="currency",
            status=KpiStatus.warning if snap["vat_estimated"] > 5000 else KpiStatus.neutral,
            trend=KpiTrend(),
            hint=(
                f"Collectée {snap['vat_collected']:.0f} € − déductible {snap['vat_deductible']:.0f} €"
            ),
        ),
        Kpi(
            id="factures_impayees",
            label="Factures impayées",
            value=float(snap["overdue_count"]),
            unit="count",
            format="integer",
            status=(
                KpiStatus.critical
                if snap["overdue_amount"] > 10000
                else KpiStatus.warning
                if snap["overdue_count"]
                else KpiStatus.ok
            ),
            trend=KpiTrend(),
            hint=f"{snap['overdue_amount']:.2f} € en retard",
        ),
        Kpi(
            id="factures_en_attente",
            label="Factures en attente",
            value=float(snap["pending_count"]),
            unit="count",
            format="integer",
            status=KpiStatus.neutral if snap["pending_count"] else KpiStatus.ok,
            trend=KpiTrend(),
            hint=f"{snap['pending_amount']:.2f} € à encaisser",
        ),
        Kpi(
            id="documents_a_traiter",
            label="Documents à traiter",
            value=float(snap["documents_to_process"]),
            unit="count",
            format="integer",
            status=KpiStatus.warning if snap["documents_to_process"] else KpiStatus.ok,
            trend=KpiTrend(),
            hint="Factures fournisseur à vérifier ou en cours d'analyse",
        ),
        Kpi(
            id="synchronisations_bancaires",
            label="Synchronisations bancaires",
            value=float(sync["connections"]),
            unit="count",
            format="integer",
            status=sync_status,
            trend=KpiTrend(),
            hint=sync_hint,
        ),
    ]
