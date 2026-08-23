"""Masquage IBAN — unique helper banking pour les surfaces utilisateur.

Ne jamais journaler la valeur d'entrée. Ne lève jamais sur une chaîne partielle.
"""

from __future__ import annotations

_BULLET = "••••"


def _compact(value: str | None) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isalnum()).upper()


def iban_last4(value: str | None) -> str | None:
    compact = _compact(value)
    if len(compact) < 4:
        return None
    return compact[-4:]


def mask_iban(value: str | None) -> str:
    """Masque un IBAN pour l'UI / l'API.

    FR76 •••• •••• •••• 1234  si le préfixe (4) et les 4 derniers sont fiables.
    •••• 1234                 si seules les dernières positions sont utilisables.
    """
    compact = _compact(value)
    if not compact:
        return ""
    if len(compact) < 4:
        return _BULLET
    last4 = compact[-4:]
    if len(compact) < 8:
        return f"{_BULLET} {last4}"
    prefix = compact[:4]
    middle = max(len(compact) - 8, 0)
    groups = max((middle + 3) // 4, 1)
    return " ".join([prefix, *([_BULLET] * groups), last4])
