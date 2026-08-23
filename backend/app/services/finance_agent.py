"""Finance Agent — façade de compatibilité vers l'AI Financial Assistant V1.

Le Decision Engine est l'unique orchestrateur conversationnel.
``answer_finance_question`` délègue ; ``pilot_kpis`` reste basé sur le Financial Engine.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models_saas import AIConversation


def _finance_snapshot(db: Session, organization_id: int | None) -> dict:
    """Instantané financier — délégué au Financial Engine (source de vérité unique)."""
    from app.financial.engine import FinancialEngine

    return FinancialEngine(db).snapshot_compat(organization_id)


def answer_finance_question(
    db: Session,
    *,
    question: str,
    user_id: int | None,
    organization_id: int | None,
) -> dict:
    """Compatibilité historique — délègue au Decision Engine."""
    from app.ai_assistant.decision_engine import DecisionEngine

    org_id = int(organization_id or 0)
    result = DecisionEngine(db).chat(
        organization_id=org_id,
        user_id=user_id,
        question=question,
    )
    snap = _finance_snapshot(db, organization_id)
    return {
        "answer": result.get("answer", ""),
        "agent": result.get("agent", "AI Financial Assistant"),
        "conversation_id": result.get("conversation_id"),
        "message_id": result.get("message_id"),
        "structured": result.get("structured"),
        "confidence": result.get("confidence"),
        "sources": result.get("sources", []),
        "tools_used": result.get("tools_used", []),
        "actions": result.get("actions", []),
        "snapshot": {
            "ca": snap.get("ca"),
            "marge_pct": snap.get("marge_pct"),
            "balance": snap.get("balance"),
            "unpaid": snap.get("unpaid"),
            "top_charge": snap.get("top_charge"),
        },
    }


def list_conversations(db: Session, organization_id: int, limit: int = 20) -> list[dict]:
    rows = (
        db.query(AIConversation)
        .filter(AIConversation.organization_id == organization_id)
        .order_by(AIConversation.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def pilot_kpis(db: Session, organization_id: int | None) -> dict:
    snap = _finance_snapshot(db, organization_id)
    balance = snap.get("balance")
    homogeneous = snap.get("treasury_homogeneous", True)
    empty = (
        not snap["has_data"]
        and (balance == 0 or balance is None)
        and snap["ca"] == 0
        and snap["charges"] == 0
    )

    if empty:
        return {
            "health": "setup",
            "ca": 0.0,
            "benefice": 0.0,
            "marge_pct": 0.0,
            "tresorerie": 0.0,
            "depenses": 0.0,
            "unpaid": 0.0,
            "forecast_30": 0.0,
            "alerts": [],
            "recommendations": [
                "Déposez une facture fournisseur et créez votre première facture client pour démarrer.",
            ],
            "evolution": {
                "ca_label": "CA facturé",
                "marge_label": "Marge",
                "cash_label": "Trésorerie",
            },
        }

    health = "ok"
    if snap["tensions"] or (
        homogeneous and balance is not None and 0 < balance < 5000
    ):
        health = "attention"
    if (
        homogeneous
        and balance is not None
        and snap["forecast"]["30"] < 3000
        and snap["charges"] > 0
    ):
        health = "critique"

    alerts: list[str] = []
    if snap["overdue_clients"]:
        alerts.append(f"{snap['overdue_clients']} client(s) en retard / impayé")
    if snap["duplicates"]:
        alerts.append(f"{snap['duplicates']} doublon(s) bancaire(s)")
    if snap["to_review"]:
        alerts.append(f"{snap['to_review']} facture(s) fournisseur à vérifier")
    if snap["tensions"]:
        alerts.extend(snap["tensions"][:2])

    return {
        "health": health,
        "ca": snap["ca"],
        "benefice": snap["marge"],
        "marge_pct": snap["marge_pct"],
        "tresorerie": balance,
        "depenses": snap["charges"],
        "unpaid": snap["unpaid"],
        "forecast_30": snap["forecast"]["30"],
        "alerts": alerts,
        "recommendations": snap["recommendations"][:3],
        "evolution": {
            "ca_label": "CA facturé (période)",
            "marge_label": f"Marge estimée {snap['marge_pct']}%",
            "cash_label": "Trésorerie",
        },
    }
