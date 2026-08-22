"""Sécurité Accounting Pipeline."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.accounting.accounting_exceptions import AccountingPermissionError, AccountingValidationError
from app.config import settings

_ACCOUNT_RE = re.compile(r"^[0-9]{3,8}$")
_MAX_DESC = 500
_MAX_COMMENT = 2000
_MAX_LINES = 50
_MAX_JSON_BYTES = 65_536


def assert_account_code(code: str) -> str:
    value = (code or "").strip()
    if not _ACCOUNT_RE.match(value):
        raise AccountingValidationError(f"Compte comptable invalide: {value or 'vide'}")
    return value


def assert_description(text: str | None, *, field: str = "description") -> str:
    value = (text or "").strip()
    if len(value) > _MAX_DESC:
        raise AccountingValidationError(f"{field} trop long (max {_MAX_DESC})")
    # Refuse formules / code exécutable grossier
    lowered = value.lower()
    for bad in ("=", "javascript:", "<script", "__import__", "eval("):
        if bad in lowered:
            raise AccountingValidationError(f"{field} contient un contenu non autorisé")
    return value


def assert_comment(text: str | None) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if len(value) > _MAX_COMMENT:
        raise AccountingValidationError(f"commentaire trop long (max {_MAX_COMMENT})")
    return value


def assert_line_count(n: int) -> None:
    if n < 0 or n > _MAX_LINES:
        raise AccountingValidationError(f"Nombre de lignes invalide (max {_MAX_LINES})")


def to_decimal(value: Any, *, field: str = "amount") -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise AccountingValidationError(f"{field} non numérique") from exc
    return d.quantize(Decimal("0.01"))


def assert_json_size(payload: dict | list, *, label: str = "json") -> None:
    import json

    size = len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
    if size > _MAX_JSON_BYTES:
        raise AccountingValidationError(f"{label} trop volumineux")


def check_accounting_permission(permissions: list[str] | set[str], action: str) -> None:
    """
    Contrôle centralisé des permissions accounting.*

    Limite V1 : si accounting.* n'est pas dans le catalogue de rôles,
    on accepte aussi '*' ou 'ai.analysis' / 'documents.write' comme fallback
    documenté (pas de fausse granularité).
    """
    perms = set(permissions or [])
    if "*" in perms:
        return
    required = f"accounting.{action}"
    if required in perms:
        return
    # Fallbacks documentés — réservés aux actions non sensibles (view/edit).
    # validate / reject / reopen exigent accounting.* explicite ou '*'.
    fallbacks = {
        "view": {"ai.analysis", "documents.read", "invoice.read"},
        "edit": {"ai.analysis", "documents.write", "invoice.create"},
        "validate": set(),
        "reject": set(),
        "reopen": set(),
    }
    if perms & fallbacks.get(action, set()):
        return
    raise AccountingPermissionError(f"Permission accounting.{action} requise")


def amount_tolerance() -> Decimal:
    return Decimal(str(settings.elfis_accounting_amount_tolerance))


def balance_tolerance() -> Decimal:
    return Decimal(str(settings.elfis_accounting_balance_tolerance))
