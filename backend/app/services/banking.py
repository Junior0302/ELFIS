from __future__ import annotations

import csv
import hashlib
import io
import unicodedata
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import BankAccount, BankTransaction, Invoice


CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("salaires", ["salaire", "paie", "urssaf", "payroll"]),
    ("loyer", ["loyer", "rent", "bail"]),
    ("publicite", ["google ads", "meta ads", "facebook ads", "publicite", "ads"]),
    ("abonnements", ["spotify", "notion", "slack", "microsoft 365", "adobe", "abonnement"]),
    ("telecom", ["orange", "sfr", "bouygues", "free pro"]),
    ("energie", ["edf", "engie", "electricite", "gaz"]),
    ("fournisseurs", ["facture", "achat", "supplier", "vir sepa"]),
    ("clients", ["virement client", "encaissement", "stripe", "paypal"]),
    ("impots", ["dgfip", "tva", "impot", "urssaf"]),
    ("banque_frais", ["commission", "frais bancaires", "agios"]),
]


def categorize(label: str) -> str:
    lowered = label.lower()
    for category, keywords in CATEGORY_RULES:
        if any(k in lowered for k in keywords):
            return category
    return "autre"


def _normalized_header(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in text if not unicodedata.combining(char)).strip().lower()


def _parse_amount(value: str) -> float:
    clean = (value or "").replace("\u202f", "").replace("\xa0", "").replace("€", "").replace(" ", "")
    if "," in clean and "." in clean:
        clean = clean.replace(".", "").replace(",", ".")
    else:
        clean = clean.replace(",", ".")
    return float(clean)


def import_bank_csv(
    db: Session,
    *,
    content: bytes,
    organization_id: int,
) -> dict:
    account = get_bank_account(db, organization_id)
    if not account or not account.connected:
        raise ValueError("Enregistrez d’abord votre compte bancaire.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    except csv.Error:
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames:
        raise ValueError("Le fichier CSV ne contient pas d’en-têtes.")

    headers = {_normalized_header(name): name for name in reader.fieldnames}

    def column(*aliases: str) -> str | None:
        return next((headers[name] for name in aliases if name in headers), None)

    date_col = column("date", "date operation", "date de l operation", "booked at")
    label_col = column("libelle", "description", "operation", "label")
    amount_col = column("montant", "amount")
    debit_col = column("debit", "montant debit")
    credit_col = column("credit", "montant credit")
    if not date_col or not label_col or not (amount_col or debit_col or credit_col):
        raise ValueError(
            "Colonnes attendues : date, libellé et montant (ou débit/crédit)."
        )

    existing_ids = {
        row[0]
        for row in db.query(BankTransaction.external_id)
        .filter(BankTransaction.account_id == account.id)
        .all()
    }
    imported = 0
    ignored = 0
    for index, row in enumerate(reader, start=2):
        label = (row.get(label_col) or "").strip()
        booked_at = (row.get(date_col) or "").strip()
        if not label or not booked_at:
            ignored += 1
            continue
        try:
            if amount_col and (row.get(amount_col) or "").strip():
                amount = _parse_amount(row.get(amount_col) or "")
            else:
                credit = _parse_amount(row.get(credit_col) or "0") if credit_col else 0.0
                debit = _parse_amount(row.get(debit_col) or "0") if debit_col else 0.0
                amount = credit - abs(debit)
        except ValueError:
            ignored += 1
            continue

        fingerprint = f"{account.id}|{booked_at}|{label}|{amount:.2f}|{index}"
        external_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:32]
        if external_id in existing_ids:
            ignored += 1
            continue
        db.add(
            BankTransaction(
                account_id=account.id,
                external_id=external_id,
                booked_at=booked_at,
                label=label,
                amount=round(amount, 2),
                currency=account.currency,
                category=categorize(label),
            )
        )
        existing_ids.add(external_id)
        imported += 1

    db.commit()
    analysis = sync_bank(db, organization_id)
    return {"imported": imported, "ignored": ignored, "analyzed": analysis["analyzed"]}


def is_legacy_demo_account(account: BankAccount) -> bool:
    name = (account.bank_name or "").strip().lower()
    label = (account.label or "").strip().lower()
    iban = account.iban or ""
    return (
        name in {"banque demo", "banque demo elfis", "compte principal"}
        or label == "compte courant pro"
        or "demo" in iban.lower()
        or abs(float(account.balance) - 18450.0) < 0.01
    )


def get_bank_account(db: Session, organization_id: int | None = None) -> BankAccount | None:
    query = db.query(BankAccount)
    if organization_id is not None:
        query = query.filter(BankAccount.organization_id == organization_id)
    account = query.order_by(BankAccount.id.asc()).first()
    if not account:
        return None
    if is_legacy_demo_account(account):
        db.query(BankTransaction).filter(BankTransaction.account_id == account.id).delete(
            synchronize_session=False
        )
        db.delete(account)
        db.commit()
        return None
    return account


def connect_bank(
    db: Session,
    *,
    bank_name: str,
    label: str = "Compte courant",
    iban: str = "",
    balance: float = 0.0,
    organization_id: int = 0,
) -> BankAccount:
    account = get_bank_account(db, organization_id)
    if account:
        account.bank_name = bank_name.strip() or account.bank_name
        account.label = label.strip() or account.label
        account.iban = iban.strip() or account.iban
        account.balance = float(balance)
        account.connected = True
        account.last_sync_at = datetime.utcnow()
    else:
        account = BankAccount(
            organization_id=organization_id,
            bank_name=bank_name.strip() or "Banque",
            label=label.strip() or "Compte courant",
            iban=iban.strip(),
            balance=float(balance),
            connected=True,
            last_sync_at=datetime.utcnow(),
        )
        db.add(account)
    db.commit()
    db.refresh(account)
    return account


def disconnect_bank(db: Session, organization_id: int | None = None) -> None:
    account = get_bank_account(db, organization_id)
    if not account:
        return
    account.connected = False
    db.add(account)
    db.commit()


def sync_bank(db: Session, organization_id: int | None = None) -> dict:
    account = get_bank_account(db, organization_id)
    if not account or not account.connected:
        raise ValueError("Aucun compte bancaire connecté. Connectez d'abord votre banque.")

    txs = (
        db.query(BankTransaction)
        .filter(BankTransaction.account_id == account.id)
        .order_by(BankTransaction.id.asc())
        .all()
    )
    for tx in txs:
        tx.is_duplicate = False
        tx.is_anomaly = False
        tx.anomaly_reason = None
        tx.reconciled = False
        tx.matched_invoice_id = None
        tx.category = categorize(tx.label)

    _detect_duplicates(txs)
    _detect_anomalies(txs)
    _reconcile_with_invoices(db, txs, account.organization_id)
    for tx in txs:
        db.add(tx)

    if txs:
        account.balance = round(float(account.balance), 2)
    account.last_sync_at = datetime.utcnow()
    db.add(account)
    db.commit()
    db.refresh(account)
    return {
        "account": account,
        "imported": 0,
        "analyzed": len(txs),
    }


def _detect_duplicates(txs: list[BankTransaction]) -> None:
    seen: dict[tuple, BankTransaction] = {}
    for tx in txs:
        key = (round(tx.amount, 2), tx.label.strip().lower(), tx.booked_at)
        if key in seen:
            tx.is_duplicate = True
            tx.anomaly_reason = "Doublon probable (même montant, libellé et date)"
            seen[key].is_duplicate = True
            if not seen[key].anomaly_reason:
                seen[key].anomaly_reason = "Doublon probable (même montant, libellé et date)"
        else:
            seen[key] = tx


def _detect_anomalies(txs: list[BankTransaction]) -> None:
    amounts = [abs(t.amount) for t in txs]
    if not amounts:
        return
    avg = sum(amounts) / len(amounts)
    for tx in txs:
        if abs(tx.amount) > max(avg * 3, 2500) and not tx.is_duplicate:
            tx.is_anomaly = True
            tx.anomaly_reason = (
                tx.anomaly_reason or f"Montant inhabituel ({tx.amount:.2f} € vs moyenne ~{avg:.0f} €)"
            )
        if "exceptionnel" in tx.label.lower():
            tx.is_anomaly = True
            tx.anomaly_reason = tx.anomaly_reason or "Libellé signalant une opération exceptionnelle"


def _reconcile_with_invoices(
    db: Session,
    txs: list[BankTransaction],
    organization_id: int,
) -> None:
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.organization_id == organization_id,
            Invoice.amount_ttc.isnot(None),
        )
        .all()
    )
    for tx in txs:
        if tx.amount >= 0:
            continue
        abs_amount = abs(tx.amount)
        for inv in invoices:
            if inv.amount_ttc is None:
                continue
            if abs(abs_amount - float(inv.amount_ttc)) <= 0.05:
                tx.reconciled = True
                tx.matched_invoice_id = inv.id
                tx.confidence = max(tx.confidence, 0.95)
                break
            if inv.invoice_number and inv.invoice_number.lower() in tx.label.lower():
                tx.reconciled = True
                tx.matched_invoice_id = inv.id
                tx.confidence = max(tx.confidence, 0.9)
                break


def list_transactions(db: Session, organization_id: int | None = None) -> list[BankTransaction]:
    account = get_bank_account(db, organization_id)
    if not account:
        return []
    return (
        db.query(BankTransaction)
        .filter(BankTransaction.account_id == account.id)
        .order_by(BankTransaction.id.desc())
        .all()
    )


def bank_overview(db: Session, organization_id: int | None = None) -> dict:
    account = get_bank_account(db, organization_id)
    if not account or is_legacy_demo_account(account):
        return {
            "account": None,
            "count": 0,
            "credits": 0.0,
            "debits": 0.0,
            "to_reconcile": 0,
            "duplicates": 0,
            "anomalies": 0,
            "transactions": [],
        }
    txs = list_transactions(db, organization_id)
    debits = sum(t.amount for t in txs if t.amount < 0)
    credits = sum(t.amount for t in txs if t.amount > 0)
    return {
        "account": account,
        "count": len(txs),
        "credits": round(credits, 2),
        "debits": round(debits, 2),
        "to_reconcile": sum(1 for t in txs if not t.reconciled and t.amount < 0),
        "duplicates": sum(1 for t in txs if t.is_duplicate),
        "anomalies": sum(1 for t in txs if t.is_anomaly or t.is_duplicate),
        "transactions": txs,
    }


def cashflow_forecast(db: Session, organization_id: int | None = None) -> dict:
    account = get_bank_account(db, organization_id)
    txs = list_transactions(db, organization_id)
    if not account:
        return {
            "current_balance": 0.0,
            "forecast": {"30": 0.0, "60": 0.0, "90": 0.0},
            "tensions": [],
            "recommendations": [
                "Connectez votre banque pour projeter la trésorerie sur 30 / 60 / 90 jours."
            ],
            "encaissements": 0.0,
            "decaissements": 0.0,
            "net_period": 0.0,
        }

    net = sum(t.amount for t in txs) if txs else 0.0
    daily = (net / 15.0) if txs else 0.0
    balance = account.balance
    day30 = round(balance + daily * 30, 2)
    day60 = round(balance + daily * 60, 2)
    day90 = round(balance + daily * 90, 2)

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
            recommendations.append("Revoir les abonnements et plafonner les dépenses publicitaires.")
        if not tensions:
            recommendations.append("Trésorerie saine à court terme — maintenir le suivi hebdomadaire.")

    credits = sum(t.amount for t in txs if t.amount > 0)
    debits = abs(sum(t.amount for t in txs if t.amount < 0))

    return {
        "current_balance": balance,
        "forecast": {"30": day30, "60": day60, "90": day90},
        "tensions": tensions,
        "recommendations": recommendations,
        "encaissements": round(credits, 2),
        "decaissements": round(debits, 2),
        "net_period": round(net, 2),
    }


def purge_demo_finance_data(db: Session) -> None:
    """Supprime uniquement les anciennes entrées de démonstration identifiables."""
    legacy_accounts = [
        account for account in db.query(BankAccount).all() if is_legacy_demo_account(account)
    ]
    for account in legacy_accounts:
        db.query(BankTransaction).filter(BankTransaction.account_id == account.id).delete(
            synchronize_session=False
        )
        db.delete(account)

    demo_filenames = {
        "demo_facture_orange.pdf",
        "4205f6c2e41a_demo_facture_orange.pdf",
    }
    db.query(Invoice).filter(Invoice.filename.in_(demo_filenames)).delete(
        synchronize_session=False
    )
    db.commit()
