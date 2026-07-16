from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.elfis_ai.intelligence import build_intelligence_overview
from app.elfis_ai.orchestrator import get_latest_analysis, report_from_analysis
from app.models import Invoice


def _cite(invoice: Invoice) -> str:
    label = invoice.invoice_number or invoice.filename
    return f"document #{invoice.id} ({label})"


def answer_elfis_chat(db: Session, organization_id: int, question: str) -> dict:
    q = (question or "").strip()
    if not q:
        return {
            "ok": False,
            "answer": "Posez une question sur vos données (dépenses, fournisseurs, anomalies…).",
            "citations": [],
            "status": "insufficient_data",
        }

    overview = build_intelligence_overview(db, organization_id, period="month")
    invoices = (
        db.query(Invoice)
        .filter(Invoice.organization_id == organization_id)
        .order_by(Invoice.id.desc())
        .limit(100)
        .all()
    )
    citations: list[str] = []
    ql = q.lower()

    # Dépenses du mois
    if any(k in ql for k in ("dépensé", "depense", "dépenses", "achats du mois", "combien")):
        expenses = overview["company_synthesis"]["expenses"]
        citations = [_cite(i) for i in invoices[:5] if i.amount_ttc]
        return {
            "ok": True,
            "answer": (
                f"Ce mois-ci, vos achats analysés totalisent {expenses:.2f} € TTC "
                f"sur {overview['company_synthesis']['documents_analyzed']} document(s)."
            ),
            "citations": citations,
            "status": "ok",
            "data_used": {"expenses": expenses},
        }

    # Fournisseur le plus coûteux
    if "fournisseur" in ql and any(k in ql for k in ("coûteux", "couteux", "cher", "plus")):
        totals: dict[str, float] = {}
        by_supplier: dict[str, list[Invoice]] = {}
        for inv in invoices:
            if not inv.supplier or inv.amount_ttc is None:
                continue
            totals[inv.supplier] = totals.get(inv.supplier, 0) + float(inv.amount_ttc)
            by_supplier.setdefault(inv.supplier, []).append(inv)
        if not totals:
            return {
                "ok": True,
                "answer": "Impossible de répondre : aucun fournisseur avec montant enregistré.",
                "citations": [],
                "status": "insufficient_data",
            }
        best = max(totals.items(), key=lambda x: x[1])
        citations = [_cite(i) for i in by_supplier[best[0]][:5]]
        return {
            "ok": True,
            "answer": f"Le fournisseur le plus coûteux (historique disponible) est {best[0]} avec {best[1]:.2f} € TTC cumulés.",
            "citations": citations,
            "status": "ok",
            "data_used": {"supplier": best[0], "total": best[1]},
        }

    # Échéances
    if any(k in ql for k in ("échéance", "echeance", "payer", "paiement")):
        lines = []
        for inv in invoices[:40]:
            analysis = get_latest_analysis(db, inv.id, organization_id)
            if not analysis:
                continue
            try:
                report = report_from_analysis(analysis)
            except Exception:
                continue
            due = report.financial_analysis.recommended_payment_date
            days = report.financial_analysis.due_in_days
            if due or days is not None:
                lines.append(
                    f"- {_cite(inv)} : échéance {due or 'n/a'}"
                    + (f" ({days} j)" if days is not None else "")
                )
                citations.append(_cite(inv))
        if not lines:
            return {
                "ok": True,
                "answer": "Aucune échéance exploitable n'est disponible dans les analyses actuelles.",
                "citations": [],
                "status": "insufficient_data",
            }
        return {
            "ok": True,
            "answer": "Échéances détectées :\n" + "\n".join(lines[:10]),
            "citations": citations[:10],
            "status": "ok",
        }

    # Anomalies
    if "anomal" in ql:
        alerts = overview.get("anomalies") or overview.get("alerts") or []
        if not alerts:
            return {
                "ok": True,
                "answer": "Aucune anomalie ouverte prioritaire n'est recensée pour l'instant.",
                "citations": [],
                "status": "ok",
            }
        lines = []
        for a in alerts[:10]:
            lines.append(f"- {a.get('title')}: {a.get('description')}")
            if a.get("document_id"):
                citations.append(f"document #{a['document_id']}")
        return {
            "ok": True,
            "answer": "Synthèse des anomalies :\n" + "\n".join(lines),
            "citations": citations,
            "status": "ok",
        }

    # Pourquoi compte 606 / imputation
    m = re.search(r"\b(60\d|445\d+|401)\b", ql) or ("imputation" in ql or "classé" in ql or "compte" in ql)
    if m:
        target = invoices[0] if invoices else None
        id_match = re.search(r"#?\b(\d+)\b", ql)
        if id_match:
            inv_id = int(id_match.group(1))
            target = next((i for i in invoices if i.id == inv_id), target)
        if not target:
            return {
                "ok": True,
                "answer": "Aucun document disponible pour expliquer l'imputation.",
                "citations": [],
                "status": "insufficient_data",
            }
        analysis = get_latest_analysis(db, target.id, organization_id)
        if not analysis:
            return {
                "ok": True,
                "answer": f"Aucune analyse ELFIS pour {_cite(target)}.",
                "citations": [_cite(target)],
                "status": "insufficient_data",
            }
        report = report_from_analysis(analysis)
        explains = []
        for line in report.accounting.lines:
            explains.append(f"{line.account}: {line.justification}")
        answer = (
            " ; ".join(explains)
            if explains
            else (report.accounting.explanations[0] if report.accounting.explanations else "Justification indisponible.")
        )
        return {
            "ok": True,
            "answer": f"Pour {_cite(target)} — {answer}",
            "citations": [_cite(target)],
            "status": "ok",
        }

    # Fallback synthétique factuel
    synth = overview["company_synthesis"]
    return {
        "ok": True,
        "answer": (
            f"Voici ce que les données autorisées permettent de dire : "
            f"{synth['documents_analyzed']} document(s) ce mois, "
            f"dépenses {synth['expenses']:.2f} €, "
            f"{synth['open_anomalies']} anomalie(s) ouverte(s). "
            "Précisez votre question (dépenses, fournisseur, échéances, anomalies, imputation)."
        ),
        "citations": [_cite(i) for i in invoices[:3]],
        "status": "ok",
        "data_used": synth,
    }
