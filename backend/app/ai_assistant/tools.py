"""Outils IA internes — le LLM n'appelle que ces fonctions.

Chaque outil lit un moteur métier (Financial, Banking, Vault…) et retourne
des faits vérifiés. Aucune invention de données.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.ai_assistant.types import ToolResult, ToolSpec
from app.banking.engine import BankingEngine
from app.financial.alerts import build_alerts
from app.financial.engine import FinancialEngine
from app.financial.health import compute_health_score
from app.models_saas import SalesDocument

ToolFn = Callable[..., ToolResult]


class AssistantTools:
    """Registre des outils accessibles au Decision Engine."""

    def __init__(self, db: Session, organization_id: int):
        self.db = db
        self.organization_id = organization_id
        self._financial = FinancialEngine(db, publish_events=False)
        self._banking = BankingEngine(db)

    def specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="get_cashflow",
                description="Trésorerie, prévisions 30/60/90 j et tensions.",
                parameters={},
            ),
            ToolSpec(
                name="get_unpaid_invoices",
                description="Factures clients impayées / en retard.",
                parameters={},
            ),
            ToolSpec(
                name="get_vat",
                description="TVA collectée, déductible et estimée.",
                parameters={},
            ),
            ToolSpec(
                name="get_expenses",
                description="Dépenses bancaires et répartition par catégorie.",
                parameters={},
            ),
            ToolSpec(
                name="get_documents",
                description="Documents fournisseur à traiter / récents.",
                parameters={"limit": {"type": "integer", "default": 8}},
            ),
            ToolSpec(
                name="search_transactions",
                description="Recherche de transactions bancaires par libellé.",
                parameters={"q": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            ),
            ToolSpec(
                name="get_kpis",
                description="Les 9 KPIs financiers standardisés.",
                parameters={},
            ),
            ToolSpec(
                name="get_alerts",
                description="Alertes financières normalisées.",
                parameters={},
            ),
            ToolSpec(
                name="get_health_score",
                description="Financial Health Score 0-100 et composants.",
                parameters={},
            ),
            ToolSpec(
                name="get_sync_status",
                description="État des synchronisations bancaires.",
                parameters={},
            ),
        ]

    def names(self) -> list[str]:
        return [s.name for s in self.specs()]

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        handlers: dict[str, ToolFn] = {
            "get_cashflow": self.get_cashflow,
            "get_unpaid_invoices": self.get_unpaid_invoices,
            "get_vat": self.get_vat,
            "get_expenses": self.get_expenses,
            "get_documents": self.get_documents,
            "search_transactions": self.search_transactions,
            "get_kpis": self.get_kpis,
            "get_alerts": self.get_alerts,
            "get_health_score": self.get_health_score,
            "get_sync_status": self.get_sync_status,
        }
        fn = handlers.get(name)
        if fn is None:
            return ToolResult(tool=name, ok=False, error=f"Outil inconnu : {name}")
        try:
            return fn(**kwargs)
        except Exception as exc:  # noqa: BLE001 — surface propre à l'assistant
            return ToolResult(tool=name, ok=False, error=str(exc)[:300])

    def _as_of(self, snap: dict | None = None) -> datetime:
        if snap and snap.get("computed_at"):
            try:
                return datetime.fromisoformat(str(snap["computed_at"]))
            except ValueError:
                pass
        return datetime.utcnow()

    def get_cashflow(self, **_: Any) -> ToolResult:
        snap = self._financial.snapshot(self.organization_id)
        return ToolResult(
            tool="get_cashflow",
            data={
                "treasury": snap["treasury"],
                "forecast": snap["forecast"],
                "tensions": snap["tensions"],
                "recommendations": snap["recommendations"][:3],
                "credits": snap["credits"],
                "expenses": snap["expenses"],
                "has_bank": snap["has_bank"],
            },
            data_as_of=self._as_of(snap),
        )

    def get_unpaid_invoices(self, **_: Any) -> ToolResult:
        snap = self._financial.snapshot(self.organization_id)
        sales = (
            self.db.query(SalesDocument)
            .filter(
                SalesDocument.organization_id == self.organization_id,
                SalesDocument.doc_type == "facture",
                SalesDocument.status.in_(["sent", "partial", "overdue", "accepted"]),
            )
            .order_by(SalesDocument.id.desc())
            .limit(20)
            .all()
        )
        items = []
        for d in sales:
            remaining = max(0.0, d.amount_ttc - d.paid_amount)
            if remaining <= 0:
                continue
            items.append(
                {
                    "number": d.number,
                    "customer": d.customer_name,
                    "status": d.status,
                    "amount_ttc": d.amount_ttc,
                    "remaining": round(remaining, 2),
                    "due_date": d.due_date,
                    "issue_date": d.issue_date,
                }
            )
        return ToolResult(
            tool="get_unpaid_invoices",
            data={
                "overdue_count": snap["overdue_count"],
                "overdue_amount": snap["overdue_amount"],
                "pending_count": snap["pending_count"],
                "pending_amount": snap["pending_amount"],
                "unpaid_amount": snap["unpaid_amount"],
                "invoices": items[:15],
            },
            data_as_of=self._as_of(snap),
        )

    def get_vat(self, **_: Any) -> ToolResult:
        snap = self._financial.snapshot(self.organization_id)
        return ToolResult(
            tool="get_vat",
            data={
                "vat_collected": snap["vat_collected"],
                "vat_deductible": snap["vat_deductible"],
                "vat_estimated": snap["vat_estimated"],
                "supplier_ht": snap["supplier_ht"],
            },
            data_as_of=self._as_of(snap),
        )

    def get_expenses(self, **_: Any) -> ToolResult:
        snap = self._financial.snapshot(self.organization_id)
        breakdown = sorted(
            (
                {"category": cat, "amount": entry["amount"], "count": entry["count"]}
                for cat, entry in snap["expense_by_category"].items()
            ),
            key=lambda x: -x["amount"],
        )
        return ToolResult(
            tool="get_expenses",
            data={
                "expenses": snap["expenses"],
                "revenue": snap["revenue"],
                "margin_pct": snap["margin_pct"],
                "profit": snap["profit"],
                "breakdown": breakdown[:10],
                "anomalies": snap["anomalies"],
            },
            data_as_of=self._as_of(snap),
        )

    def get_documents(self, *, limit: int = 8, **_: Any) -> ToolResult:
        snap = self._financial.snapshot(self.organization_id)
        activity = [
            a
            for a in self._financial.recent_activity(self.organization_id, limit=limit * 2)
            if a["type"] == "document"
        ][: max(1, min(int(limit), 20))]
        return ToolResult(
            tool="get_documents",
            data={
                "documents_to_process": snap["documents_to_process"],
                "to_review": snap["to_review"],
                "recent": activity,
            },
            data_as_of=self._as_of(snap),
        )

    def search_transactions(self, *, q: str = "", limit: int = 10, **_: Any) -> ToolResult:
        items, total = self._banking.list_transactions(
            self.organization_id,
            search=(q or "").strip() or None,
            limit=max(1, min(int(limit), 50)),
        )
        return ToolResult(
            tool="search_transactions",
            data={
                "total": total,
                "query": q,
                "transactions": [
                    {
                        "id": t.id,
                        "label": t.label,
                        "amount": t.amount,
                        "booked_at": t.booked_at,
                        "category": t.category,
                        "status": getattr(t, "status", "booked"),
                    }
                    for t in items
                ],
            },
            data_as_of=datetime.utcnow(),
        )

    def get_kpis(self, **_: Any) -> ToolResult:
        kpis = self._financial.kpis(self.organization_id)
        snap = self._financial.snapshot(self.organization_id)
        return ToolResult(
            tool="get_kpis",
            data={
                "kpis": [
                    {
                        "id": k.id,
                        "label": k.label,
                        "value": k.value,
                        "unit": k.unit,
                        "status": k.status.value,
                        "hint": k.hint,
                    }
                    for k in kpis
                ]
            },
            data_as_of=self._as_of(snap),
        )

    def get_alerts(self, **_: Any) -> ToolResult:
        snap = self._financial.snapshot(self.organization_id)
        alerts = build_alerts(snap)
        return ToolResult(
            tool="get_alerts",
            data={
                "alerts": [
                    {
                        "code": a.code,
                        "severity": a.severity.value,
                        "title": a.title,
                        "message": a.message,
                        "action": a.action,
                    }
                    for a in alerts
                ]
            },
            data_as_of=self._as_of(snap),
        )

    def get_health_score(self, **_: Any) -> ToolResult:
        snap = self._financial.snapshot(self.organization_id)
        health = compute_health_score(snap)
        return ToolResult(
            tool="get_health_score",
            data=health,
            data_as_of=self._as_of(snap),
        )

    def get_sync_status(self, **_: Any) -> ToolResult:
        snap = self._financial.snapshot(self.organization_id)
        return ToolResult(
            tool="get_sync_status",
            data=snap["sync"],
            data_as_of=self._as_of(snap),
        )


# Intention → outils à appeler (routing déterministe, sans LLM)
INTENT_TOOLS: dict[str, list[str]] = {
    "cashflow": ["get_cashflow", "get_sync_status", "get_alerts"],
    "unpaid": ["get_unpaid_invoices", "get_alerts"],
    "vat": ["get_vat", "get_documents"],
    "expenses": ["get_expenses", "get_alerts"],
    "documents": ["get_documents"],
    "transactions": ["search_transactions"],
    "health": ["get_health_score", "get_kpis", "get_alerts"],
    "kpis": ["get_kpis", "get_health_score"],
    "overview": ["get_kpis", "get_alerts", "get_cashflow", "get_health_score"],
    "help": [],
}


def detect_intent(question: str) -> str:
    q = question.lower()
    if any(k in q for k in ("aide", "que peux", "que fais", "comment fonctionne", "help")):
        return "help"
    if any(k in q for k in ("trésor", "tresorerie", "cash", "solde", "liquid", "forecast", "prévision", "prevision")):
        return "cashflow"
    if any(k in q for k in ("impay", "retard", "relance", "client")):
        return "unpaid"
    if any(k in q for k in ("tva", "impôt", "impot", "fiscal")):
        return "vat"
    if any(k in q for k in ("dépens", "depens", "charge", "marge", "bénéfice", "benefice", "rentab")):
        return "expenses"
    if any(k in q for k in ("document", "facture fournisseur", "à traiter", "a traiter")):
        return "documents"
    if any(k in q for k in ("transaction", "opération", "operation", "virement", "chercher", "recherche")):
        return "transactions"
    if any(k in q for k in ("santé", "sante", "health", "score")):
        return "health"
    if any(k in q for k in ("kpi", "indicateur", "tableau de bord", "dashboard", "vue d'ensemble", "résumé", "resume")):
        return "overview"
    return "overview"
