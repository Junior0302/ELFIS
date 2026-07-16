from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Invoice
from app.models_saas import AIConversation, SalesDocument
from app.services.banking import bank_overview, cashflow_forecast, categorize


def _conversational_answer(
    db: Session,
    *,
    question: str,
    snapshot: dict,
    user_id: int | None,
    organization_id: int | None,
) -> str | None:
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI

        history: list[dict[str, str]] = []
        if user_id and organization_id:
            previous = (
                db.query(AIConversation)
                .filter(
                    AIConversation.user_id == user_id,
                    AIConversation.organization_id == organization_id,
                )
                .order_by(AIConversation.created_at.desc())
                .limit(4)
                .all()
            )
            for item in reversed(previous):
                history.extend(
                    [
                        {"role": "user", "content": item.question},
                        {"role": "assistant", "content": item.answer},
                    ]
                )

        safe_snapshot = {
            key: snapshot[key]
            for key in (
                "has_data",
                "ca",
                "marge",
                "marge_pct",
                "balance",
                "unpaid",
                "charges",
                "supplier_vat",
                "overdue_clients",
            )
        }
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0.35,
            max_tokens=350,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es Finance Agent, copilote français chaleureux d'un dirigeant. "
                        "Tu peux tenir une conversation naturelle, pas seulement parler de finance. "
                        "Réponds en français, avec simplicité et en 2 à 6 phrases. "
                        "N'invente jamais de chiffres, clients, opérations ou fonctionnalités. "
                        "Quand une question concerne l'entreprise, utilise uniquement l'instantané JSON. "
                        "Si une donnée manque, dis-le clairement et indique l'action réelle à effectuer. "
                        f"Instantané financier: {json.dumps(safe_snapshot, ensure_ascii=False)}"
                    ),
                },
                *history,
                {"role": "user", "content": question},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        return None


def _finance_snapshot(db: Session, organization_id: int | None) -> dict:
    bank = bank_overview(db, organization_id)
    cash = cashflow_forecast(db, organization_id)
    invoices = db.query(Invoice)
    if organization_id is not None:
        invoices = invoices.filter(Invoice.organization_id == organization_id)
    inv_ht = invoices.with_entities(func.coalesce(func.sum(Invoice.amount_ht), 0.0)).scalar() or 0.0
    inv_tva = invoices.with_entities(func.coalesce(func.sum(Invoice.amount_tva), 0.0)).scalar() or 0.0
    to_review = invoices.filter(Invoice.needs_review.is_(True)).count()

    q = db.query(SalesDocument)
    if organization_id:
        q = q.filter(SalesDocument.organization_id == organization_id)
    sales = q.all()
    ca = sum(d.amount_ht for d in sales if d.doc_type == "facture" and d.status != "cancelled")
    unpaid = sum(
        max(0.0, d.amount_ttc - d.paid_amount)
        for d in sales
        if d.doc_type == "facture" and d.status in {"sent", "partial", "overdue", "accepted"}
    )
    overdue_clients = len(
        {
            d.customer_name
            for d in sales
            if d.doc_type == "facture" and (d.status == "overdue" or (d.amount_ttc - d.paid_amount) > 0)
        }
    )

    charges = abs(bank["debits"])
    marge = round(ca - charges, 2) if ca or charges else 0.0
    marge_pct = round((marge / ca) * 100, 1) if ca else 0.0

    by_cat: dict[str, float] = {}
    for tx in bank["transactions"]:
        if tx.amount >= 0:
            continue
        cat = tx.category or categorize(tx.label)
        by_cat[cat] = by_cat.get(cat, 0.0) + abs(tx.amount)
    top_charge = max(by_cat.items(), key=lambda x: x[1]) if by_cat else ("autre", 0.0)

    return {
        "balance": float(bank["account"].balance) if bank["account"] else 0.0,
        "credits": bank["credits"],
        "debits": bank["debits"],
        "duplicates": bank["duplicates"],
        "anomalies": bank["anomalies"],
        "to_reconcile": bank["to_reconcile"],
        "forecast": cash["forecast"],
        "tensions": cash["tensions"],
        "recommendations": cash["recommendations"],
        "supplier_ht": float(inv_ht),
        "supplier_vat": float(inv_tva),
        "to_review": int(to_review),
        "ca": round(ca, 2),
        "unpaid": round(unpaid, 2),
        "overdue_clients": overdue_clients,
        "charges": round(charges, 2),
        "marge": marge,
        "marge_pct": marge_pct,
        "top_charge": {"category": top_charge[0], "amount": round(top_charge[1], 2)},
        "has_data": bool(bank["account"] or sales or inv_ht or to_review),
    }


def answer_finance_question(
    db: Session,
    *,
    question: str,
    user_id: int | None,
    organization_id: int | None,
) -> dict:
    snap = _finance_snapshot(db, organization_id)
    q = question.lower().strip()
    q_norm = "".join(c for c in q if c.isalnum() or c.isspace()).strip()
    empty = not snap["has_data"]

    greetings = {
        "bonjour",
        "bonsoir",
        "salut",
        "hello",
        "hi",
        "hey",
        "coucou",
        "hola",
        "yo",
        "bonne journee",
        "bonne soiree",
    }
    thanks = {"merci", "merci beaucoup", "thanks", "thank you", "nickel", "parfait", "super"}
    help_words = {
        "aide",
        "help",
        "que peux tu faire",
        "que peux-tu faire",
        "comment ca marche",
        "comment ça marche",
    }
    asks_wellbeing = any(
        phrase in q_norm
        for phrase in (
            "ca va",
            "comment vas tu",
            "tu vas bien",
            "comment allez vous",
            "vous allez bien",
        )
    )
    says_wellbeing = any(
        phrase in q_norm
        for phrase in ("je vais bien", "moi ca va", "ca va bien", "tout va bien")
    )

    if asks_wellbeing:
        answer = (
            "Salut ! Oui, tout va bien, merci 😊 Et vous, comment allez-vous ? "
            "On peut discuter tranquillement ou regarder un sujet financier quand vous voulez."
        )
    elif says_wellbeing:
        answer = (
            "Tant mieux 😊 Que souhaitez-vous faire aujourd’hui ? "
            "Je peux vous aider sur l’entreprise, ou simplement répondre à vos questions."
        )
    elif any(phrase in q_norm for phrase in ("qui es tu", "comment tu tappelles", "ton nom")):
        answer = (
            "Je suis Finance Agent, votre copilote dans ComptaPilot IA. "
            "Je suis là pour discuter avec vous et rendre vos chiffres faciles à comprendre."
        )
    elif (
        q_norm in greetings
        or q in greetings
        or (len(q_norm) <= 16 and any(g == q_norm or q_norm.startswith(g + " ") for g in greetings))
    ):
        if empty:
            answer = (
                "Bonjour ! Je suis votre Finance Agent, le copilote du dirigeant. "
                "Ravi de vous parler. Pour l’instant je n’ai pas encore vos chiffres sous la main — "
                "déposez une facture ou créez votre première facture client, puis reparlez-moi. "
                "En attendant, vous pouvez me demander « Que peux-tu faire ? »."
            )
        else:
            answer = (
                "Bonjour ! Content de vous retrouver. "
                "Je peux vous expliquer votre chiffre d’affaires, votre marge, "
                "votre trésorerie, vos impayés ou un investissement. "
                "Par où souhaitez-vous commencer ?"
            )
    elif q_norm in thanks or any(t == q_norm or q_norm.startswith(t + " ") for t in thanks):
        answer = (
            "Avec plaisir. Je reste à votre disposition dès que vous avez une autre question."
        )
    elif (
        q_norm in help_words
        or "que peux" in q
        or "que fais" in q
        or "comment fonctionne" in q
        or "comment ca marche" in q
        or "comment ça marche" in q
    ):
        answer = (
            "Je suis votre copilote financier. Posez vos questions comme à un directeur financier, "
            "par exemple :\n"
            "• Pourquoi ma marge baisse-t-elle ?\n"
            "• Quel est l’état de ma trésorerie ?\n"
            "• Quels clients sont en retard ?\n"
            "• Puis-je investir dans un véhicule à 40 000 € ?\n"
            "• Où en est ma TVA récupérable ?\n"
            "Je m’appuie sur votre facturation et vos factures fournisseur."
        )
    elif any(k in q for k in ("bénéfice", "benefice", "marge", "rentab")):
        if empty:
            answer = (
                "Je n'ai pas encore de chiffre d'affaires ni de dépenses à comparer. "
                "Créez une facture client et déposez vos factures fournisseur, "
                "et je pourrai analyser votre marge."
            )
        else:
            top = snap["top_charge"]
            answer = (
                f"Votre chiffre d'affaires facturé s'élève à {snap['ca']:.2f} € HT. "
                f"Les décaissements bancaires totalisent {snap['charges']:.2f} €. "
                f"Marge estimée : {snap['marge']:.2f} € ({snap['marge_pct']}%). "
                f"Le poste de charge le plus élevé est « {top['category']} » "
                f"({top['amount']:.2f} €). "
                + (
                    "La baisse de marge vient principalement de ces dépenses."
                    if snap["marge_pct"] < 15
                    else "La rentabilité reste sous contrôle à court terme."
                )
            )
    elif any(k in q for k in ("trésor", "tresorerie", "cash", "solde", "liquid")):
        if empty or snap["balance"] == 0 and not snap["charges"]:
            answer = (
                "Je n’ai pas encore assez d’encaissements et de paiements enregistrés pour calculer "
                "une position de trésorerie fiable. Renseignez vos factures et leurs paiements, "
                "puis reposez-moi la question."
            )
        else:
            f = snap["forecast"]
            tensions = " ".join(snap["tensions"]) or "Aucune tension critique détectée."
            reco = " ".join(snap["recommendations"][:2])
            answer = (
                f"Solde bancaire actuel : {snap['balance']:.2f} €. "
                f"Projection 30 j : {f['30']:.2f} € · 60 j : {f['60']:.2f} € · 90 j : {f['90']:.2f} €. "
                f"{tensions} {reco}"
            )
    elif any(k in q for k in ("impay", "client", "retard", "relance")):
        if snap["unpaid"] <= 0 and snap["overdue_clients"] <= 0:
            answer = (
                "Je ne vois pas d'impayés clients pour le moment. "
                "Dès que vous émettrez des factures et enregistrerez les paiements, "
                "je pourrai vous signaler les retards et suggérer des relances."
            )
        else:
            answer = (
                f"Montant client en retard / impayé : {snap['unpaid']:.2f} € "
                f"sur environ {snap['overdue_clients']} client(s). "
                "Recommandation : relancer les factures échues et conditionner les nouveaux devis."
            )
    elif any(k in q for k in ("tva", "impôt", "impot", "fiscal")):
        if snap["supplier_ht"] <= 0 and snap["supplier_vat"] <= 0:
            answer = (
                "Aucune facture fournisseur n'est encore disponible pour estimer la TVA. "
                "Déposez vos factures dans Déposer une facture, puis revenez me poser la question."
            )
        else:
            answer = (
                f"TVA récupérable estimée sur factures fournisseur : {snap['supplier_vat']:.2f} €. "
                f"Dépenses fournisseurs HT : {snap['supplier_ht']:.2f} €. "
                f"{snap['to_review']} document(s) à vérifier avant clôture."
            )
    elif any(k in q for k in ("doublon", "anomal", "risque", "fraude")):
        if snap["duplicates"] == 0 and snap["anomalies"] == 0:
            answer = (
                "Je ne détecte pas d’anomalie dans les données actuellement disponibles. "
                "Déposez vos documents réels pour enrichir mes contrôles."
            )
        else:
            answer = (
                f"La banque signale {snap['duplicates']} doublon(s) et {snap['anomalies']} anomalie(s). "
                f"{snap['to_reconcile']} débit(s) restent à rapprocher. "
                "Priorisez le traitement des doublons avant les exports FEC."
            )
    elif any(k in q for k in ("véhicule", "vehicule", "acheter", "investir", "40000", "40 000")):
        if empty or snap["balance"] == 0:
            answer = (
                "Pour juger un investissement (par exemple un véhicule à 40 000 €), "
                "j’ai besoin de données réelles sur vos encaissements, vos charges et vos factures. "
                "Complétez-les, puis reposez-moi la question."
            )
        else:
            ok = snap["balance"] > 40000 and snap["forecast"]["30"] > 15000
            answer = (
                f"Avec un solde de {snap['balance']:.2f} € et une projection 30 j à "
                f"{snap['forecast']['30']:.2f} €, "
                + (
                    "l'achat d'un véhicule à 40 000 € est envisageable, mais il est préférable d'attendre "
                    "2–3 mois pour préserver un coussin de trésorerie."
                    if not ok
                    else "cet achat est possible sans mettre immédiatement la trésorerie en danger — "
                    "vérifiez tout de même l'impact fiscal (amortissement / TVA)."
                )
            )
    elif any(k in q for k in ("dépens", "depens", "charge", "pourquoi", "baisse", "augmente")):
        if empty:
            answer = (
                "Je n'ai pas encore de flux de dépenses à analyser. "
                "Une fois les factures renseignées, je pourrai expliquer "
                "ce qui pèse sur votre résultat."
            )
        else:
            top = snap["top_charge"]
            answer = (
                f"Encaissements : {snap['credits']:.2f} € · Décaissements : {snap['charges']:.2f} €. "
                f"Le poste « {top['category']} » pèse {top['amount']:.2f} €. "
                f"CA facturé : {snap['ca']:.2f} € HT · marge estimée {snap['marge_pct']}%. "
                "Si les charges montent plus vite que le CA, la marge nette diminue."
            )
    else:
        conversational = _conversational_answer(
            db,
            question=question,
            snapshot=snap,
            user_id=user_id,
            organization_id=organization_id,
        )
        if conversational:
            answer = conversational
        elif empty:
            answer = (
                "Je vous écoute. Pour une réponse précise, j’ai besoin de vos données réelles. "
                "Commencez par déposer une facture ou créer une facture client — "
                "ou demandez-moi « Que peux-tu faire ? » pour voir des exemples."
            )
        else:
            answer = (
                "Bien reçu. Pouvez-vous préciser le sujet : marge, trésorerie, impayés, "
                "TVA ou un investissement ? "
                "Je vous répondrai avec les chiffres de votre entreprise."
            )

    conversation_id = None
    if user_id and organization_id:
        row = AIConversation(
            user_id=user_id,
            organization_id=organization_id,
            question=question.strip(),
            answer=answer,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        conversation_id = row.id

    return {
        "answer": answer,
        "agent": "Finance Agent",
        "conversation_id": conversation_id,
        "snapshot": {
            "ca": snap["ca"],
            "marge_pct": snap["marge_pct"],
            "balance": snap["balance"],
            "unpaid": snap["unpaid"],
            "top_charge": snap["top_charge"],
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
    empty = not snap["has_data"] and snap["balance"] == 0 and snap["ca"] == 0 and snap["charges"] == 0

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
    if snap["tensions"] or (snap["balance"] > 0 and snap["balance"] < 5000):
        health = "attention"
    if snap["forecast"]["30"] < 3000 and snap["charges"] > 0:
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
        "tresorerie": snap["balance"],
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
