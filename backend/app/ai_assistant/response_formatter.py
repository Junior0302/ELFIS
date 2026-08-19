"""Formatage déterministe des réponses — faits / estimations / recommandations / manques.

Le LLM peut enrichir le résumé, mais les chiffres viennent exclusivement des outils.
En absence de LLM (ou en fallback), ce module produit une réponse complète et sûre.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.ai_assistant.types import (
    ConfidenceLevel,
    Explanation,
    ProposedAction,
    Recommendation,
    StructuredAnswer,
    ToolResult,
)


def _euro(value: float) -> str:
    return f"{value:,.2f} €".replace(",", " ").replace(".", ",")


def _as_of(results: list[ToolResult]) -> datetime | None:
    dates = [r.data_as_of for r in results if r.data_as_of]
    return max(dates) if dates else datetime.utcnow()


def _by_tool(results: list[ToolResult]) -> dict[str, ToolResult]:
    return {r.tool: r for r in results if r.ok}


def build_actions(intent: str, by: dict[str, ToolResult]) -> list[ProposedAction]:
    actions: list[ProposedAction] = [
        ProposedAction(
            id="open_dashboard",
            label="Afficher le Dashboard",
            href="/finance",
            description="Ouvrir le tableau de bord financier",
        )
    ]
    if intent in {"unpaid", "overview"} or "get_unpaid_invoices" in by:
        actions.append(
            ProposedAction(
                id="view_invoices",
                label="Voir les factures concernées",
                href="/facturation",
                description="Ouvrir la facturation client",
            )
        )
        actions.append(
            ProposedAction(
                id="create_reminder",
                label="Créer un rappel",
                href="/facturation",
                requires_confirmation=True,
                description="Préparer une relance client (confirmation requise)",
            )
        )
    if intent in {"transactions", "expenses", "cashflow"} or "search_transactions" in by:
        actions.append(
            ProposedAction(
                id="open_transaction",
                label="Ouvrir une transaction",
                href="/banque",
                description="Consulter les transactions bancaires",
            )
        )
    if intent in {"documents"} or "get_documents" in by:
        actions.append(
            ProposedAction(
                id="view_documents",
                label="Voir les documents à traiter",
                href="/documents",
                description="Ouvrir le centre documentaire",
            )
        )
    actions.append(
        ProposedAction(
            id="prepare_report",
            label="Préparer un rapport",
            href="/reports",
            requires_confirmation=True,
            description="Générer un rapport financier (confirmation requise)",
        )
    )
    return actions


def format_deterministic(intent: str, results: list[ToolResult], *, question: str = "") -> StructuredAnswer:
    """Construit une StructuredAnswer 100 % déterministe à partir des outils."""
    by = _by_tool(results)
    facts: list[str] = []
    estimates: list[str] = []
    missing: list[str] = []
    recommendations: list[Recommendation] = []
    sources: list[str] = [r.tool for r in results if r.ok]
    as_of = _as_of(results)
    confidence = ConfidenceLevel.high if sources else ConfidenceLevel.low

    if intent == "help" or not results:
        return StructuredAnswer(
            summary=(
                "Je suis votre AI Financial Assistant. "
                "Je m'appuie uniquement sur vos moteurs internes (Financial, Banking, Vault). "
                "Posez une question sur la trésorerie, les impayés, la TVA, les dépenses ou la santé financière."
            ),
            facts=[
                "Les chiffres proviennent du Financial Engine — je n'invente jamais de données.",
                "Chaque recommandation expose pourquoi, quelles données, quel calcul et le niveau de confiance.",
            ],
            estimates=[],
            recommendations=[],
            missing=["Posez une question concrète pour que je charge les indicateurs."],
            confidence=ConfidenceLevel.high,
            sources=["decision_engine"],
            tools_used=[],
            actions=build_actions("overview", {}),
            data_as_of=datetime.utcnow(),
        )

    cash = by.get("get_cashflow")
    if cash:
        d = cash.data
        if d.get("has_bank"):
            facts.append(f"Trésorerie actuelle : {_euro(float(d['treasury']))}.")
            fc = d.get("forecast") or {}
            estimates.append(
                f"Projection de trésorerie — 30 j : {_euro(float(fc.get('30', 0)))}, "
                f"60 j : {_euro(float(fc.get('60', 0)))}, 90 j : {_euro(float(fc.get('90', 0)))}."
            )
            for t in d.get("tensions") or []:
                estimates.append(str(t))
            for reco in (d.get("recommendations") or [])[:2]:
                recommendations.append(
                    Recommendation(
                        text=str(reco),
                        explanation=Explanation(
                            why="Issue de la prévision de trésorerie du Financial Engine.",
                            data_used=["treasury", "forecast", "bank_transactions"],
                            calculation="Solde + rythme journalier net × horizon (30/60/90).",
                            confidence=ConfidenceLevel.medium,
                            data_as_of=cash.data_as_of,
                        ),
                    )
                )
        else:
            missing.append("Aucune banque connectée — la trésorerie n'est pas fiable.")

    unpaid = by.get("get_unpaid_invoices")
    if unpaid:
        d = unpaid.data
        facts.append(
            f"Factures en retard : {d.get('overdue_count', 0)} "
            f"pour {_euro(float(d.get('overdue_amount', 0)))}."
        )
        facts.append(
            f"Factures en attente : {d.get('pending_count', 0)} "
            f"pour {_euro(float(d.get('pending_amount', 0)))}."
        )
        if d.get("overdue_count"):
            recommendations.append(
                Recommendation(
                    text="Relancer les clients en retard et conditionner les nouveaux devis.",
                    explanation=Explanation(
                        why="Des factures clients ont dépassé leur échéance.",
                        data_used=["sales_documents.status", "sales_documents.due_date", "paid_amount"],
                        calculation="remaining = amount_ttc − paid_amount ; overdue si due_date < today.",
                        confidence=ConfidenceLevel.high,
                        data_as_of=unpaid.data_as_of,
                    ),
                    action=ProposedAction(
                        id="view_invoices",
                        label="Voir les factures concernées",
                        href="/facturation",
                    ),
                )
            )

    vat = by.get("get_vat")
    if vat:
        d = vat.data
        facts.append(
            f"TVA collectée : {_euro(float(d.get('vat_collected', 0)))} · "
            f"déductible : {_euro(float(d.get('vat_deductible', 0)))}."
        )
        estimates.append(
            f"TVA estimée à provisionner : {_euro(float(d.get('vat_estimated', 0)))} "
            "(collectée − déductible)."
        )

    expenses = by.get("get_expenses")
    if expenses:
        d = expenses.data
        facts.append(
            f"Dépenses bancaires cumulées : {_euro(float(d.get('expenses', 0)))} · "
            f"CA : {_euro(float(d.get('revenue', 0)))} · marge {d.get('margin_pct', 0)} %."
        )
        breakdown = d.get("breakdown") or []
        if breakdown:
            top = breakdown[0]
            facts.append(
                f"Poste de charge principal : « {top['category']} » "
                f"({_euro(float(top['amount']))})."
            )
        if d.get("anomalies"):
            estimates.append(
                f"{d['anomalies']} opération(s) bancaire(s) signalée(s) comme inhabituelle(s)."
            )

    docs = by.get("get_documents")
    if docs:
        d = docs.data
        facts.append(f"Documents à traiter : {d.get('documents_to_process', 0)}.")
        if d.get("documents_to_process"):
            recommendations.append(
                Recommendation(
                    text="Traiter les documents fournisseur en attente avant clôture.",
                    explanation=Explanation(
                        why="Des factures fournisseur nécessitent une revue ou sont en analyse.",
                        data_used=["invoices.needs_review", "invoices.status"],
                        calculation="documents_to_process = to_review + processing.",
                        confidence=ConfidenceLevel.high,
                        data_as_of=docs.data_as_of,
                    ),
                    action=ProposedAction(
                        id="view_documents",
                        label="Voir les documents à traiter",
                        href="/documents",
                    ),
                )
            )

    txs = by.get("search_transactions")
    if txs:
        d = txs.data
        facts.append(f"{d.get('total', 0)} transaction(s) correspondent à « {d.get('query', '')} ».")
        for t in (d.get("transactions") or [])[:5]:
            facts.append(
                f"{t.get('booked_at', '')} — {t.get('label', '')} : {_euro(float(t.get('amount', 0)))}."
            )

    kpis = by.get("get_kpis")
    if kpis and intent in {"overview", "kpis", "health"}:
        for k in (kpis.data.get("kpis") or [])[:6]:
            unit = " €" if k.get("unit") == "EUR" else ""
            facts.append(f"{k['label']} : {k['value']}{unit} (statut {k['status']}).")

    health = by.get("get_health_score")
    if health:
        d = health.data
        if d.get("state") == "setup":
            missing.append(d.get("message") or "Données insuffisantes pour le Health Score.")
        else:
            facts.append(
                f"Health Score : {d.get('score')}/100 (grade {d.get('grade')})."
            )

    sync = by.get("get_sync_status")
    if sync:
        d = sync.data
        facts.append(
            f"Synchronisations bancaires : {d.get('connections', 0)} connexion(s), "
            f"statut « {d.get('status')} »."
        )
        if d.get("status") in {"stale", "error", "none"}:
            missing.append("La synchronisation bancaire n'est pas à jour.")

    alerts = by.get("get_alerts")
    if alerts:
        for a in (alerts.data.get("alerts") or [])[:3]:
            estimates.append(f"Alerte [{a.get('severity')}] {a.get('title')} — {a.get('message')}")

    if not facts and not estimates:
        missing.append("Aucune donnée pertinente n'a été trouvée pour cette question.")
        confidence = ConfidenceLevel.low

    summary = _summary(intent, by, facts)
    return StructuredAnswer(
        summary=summary,
        facts=facts,
        estimates=estimates,
        recommendations=recommendations,
        missing=missing,
        confidence=confidence,
        sources=sources,
        tools_used=sources,
        actions=build_actions(intent, by),
        data_as_of=as_of,
    )


def _summary(intent: str, by: dict[str, ToolResult], facts: list[str]) -> str:
    if intent == "cashflow" and "get_cashflow" in by:
        t = by["get_cashflow"].data.get("treasury", 0)
        return f"Votre trésorerie s'élève à {_euro(float(t))}."
    if intent == "unpaid" and "get_unpaid_invoices" in by:
        d = by["get_unpaid_invoices"].data
        return (
            f"Vous avez {d.get('overdue_count', 0)} facture(s) en retard "
            f"pour {_euro(float(d.get('overdue_amount', 0)))}."
        )
    if intent == "vat" and "get_vat" in by:
        return f"TVA estimée : {_euro(float(by['get_vat'].data.get('vat_estimated', 0)))}."
    if intent == "health" and "get_health_score" in by:
        h = by["get_health_score"].data
        if h.get("score") is not None:
            return f"Votre Health Score est de {h['score']}/100 (grade {h.get('grade')})."
    if facts:
        return facts[0]
    return "Voici ce que je peux confirmer à partir de vos données internes."


def merge_llm_enrichment(base: StructuredAnswer, llm_payload: dict[str, Any] | None) -> StructuredAnswer:
    """Le LLM peut reformuler summary / ajouter des recommandations textuelles,
    mais ne peut pas modifier les faits chiffrés (déjà figés).
    """
    if not llm_payload or not isinstance(llm_payload, dict):
        return base
    summary = str(llm_payload.get("summary") or "").strip()
    if summary and len(summary) < 600:
        # Refuse les chiffres inventés : si le résumé contient un montant €
        # non présent dans les faits, on garde le résumé déterministe.
        base_text = " ".join(base.facts + base.estimates)
        suspicious = False
        for token in summary.replace(",", ".").split():
            if token.endswith("€") or (token.replace(".", "", 1).isdigit() and "€" in summary):
                if token.rstrip("€.") not in base_text.replace(",", "."):
                    # chiffre potentiellement inventé → ignore le summary LLM
                    if any(c.isdigit() for c in token):
                        suspicious = True
                        break
        if not suspicious:
            base.summary = summary

    extra_recs = llm_payload.get("recommendations")
    if isinstance(extra_recs, list):
        for item in extra_recs[:2]:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            why = str(item.get("why") or "Reformulation à partir des faits fournis.").strip()
            if not text:
                continue
            base.recommendations.append(
                Recommendation(
                    text=text[:400],
                    explanation=Explanation(
                        why=why[:400],
                        data_used=list(base.sources),
                        calculation="Reformulation LLM — aucun nouveau calcul.",
                        confidence=ConfidenceLevel.low,
                        data_as_of=base.data_as_of,
                    ),
                )
            )
    return base
