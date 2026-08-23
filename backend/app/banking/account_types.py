"""Types de compte ELFIS — indépendants des enums fournisseurs."""

from __future__ import annotations

from enum import Enum


class BankAccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    card = "card"
    loan = "loan"
    investment = "investment"
    other = "other"


_ALIASES: dict[str, BankAccountType] = {
    "checking": BankAccountType.checking,
    "current": BankAccountType.checking,
    "compte_courant": BankAccountType.checking,
    "cash": BankAccountType.checking,
    "deposit": BankAccountType.checking,
    "savings": BankAccountType.savings,
    "saving": BankAccountType.savings,
    "livret": BankAccountType.savings,
    "pea": BankAccountType.savings,
    "card": BankAccountType.card,
    "credit_card": BankAccountType.card,
    "card_account": BankAccountType.card,
    "loan": BankAccountType.loan,
    "mortgage": BankAccountType.loan,
    "revolving": BankAccountType.loan,
    "consumer": BankAccountType.loan,
    "investment": BankAccountType.investment,
    "market": BankAccountType.investment,
    "life_insurance": BankAccountType.investment,
    "lifeinsurance": BankAccountType.investment,
    "equity": BankAccountType.investment,
    "other": BankAccountType.other,
    "unknown": BankAccountType.other,
}


def normalize_account_type(raw: object | None) -> str:
    text = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    mapped = _ALIASES.get(text)
    if mapped:
        return mapped.value
    return BankAccountType.other.value
