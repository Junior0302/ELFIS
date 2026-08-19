"""Normalisation bornée — Decimal pour montants, jamais float persisté."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

_AMOUNT_RE = re.compile(
    r"(?<!\d)(\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d{1,2})?|\d+[.,]\d{1,2}|\d+)(?!\d)"
)
_PCT_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[.,]\d{1,2})?)\s*%")
_CURRENCY_MAP = {
    "€": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "$": "USD",
    "usd": "USD",
    "£": "GBP",
    "gbp": "GBP",
    "chf": "CHF",
}
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_FR_DATE = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$")
_AMBIGUOUS_DATE = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})$")


class ExtractionNormalizationService:
    def normalize_string(self, raw: Any, *, max_len: int = 2000) -> str | None:
        if raw is None:
            return None
        s = str(raw).strip()
        s = re.sub(r"\s+", " ", s)
        if not s:
            return None
        if len(s) > max_len:
            raise ValueError("field_too_long")
        return s

    def normalize_decimal(self, raw: Any) -> Decimal | None:
        if raw is None or raw == "":
            return None
        if isinstance(raw, Decimal):
            return raw
        if isinstance(raw, (int,)):
            return Decimal(raw)
        s = str(raw).strip().replace("\u00a0", " ").replace(" ", "")
        if not s:
            return None
        # FR: 1.234,56 ou 1234,56 ; EN: 1,234.56 ou 1234.56
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            parts = s.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                s = s.replace(",", ".")
            else:
                s = s.replace(",", "")
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("invalid_decimal") from exc

    def normalize_percentage(self, raw: Any) -> Decimal | None:
        if raw is None or raw == "":
            return None
        s = str(raw).strip()
        m = _PCT_RE.search(s)
        if m:
            return self.normalize_decimal(m.group(1))
        return self.normalize_decimal(s)

    def normalize_currency(self, raw: Any) -> str | None:
        if raw is None or raw == "":
            return None
        s = str(raw).strip().lower()
        if s in _CURRENCY_MAP:
            return _CURRENCY_MAP[s]
        up = str(raw).strip().upper()
        if len(up) == 3 and up.isalpha():
            return up
        raise ValueError("invalid_currency")

    def normalize_date(self, raw: Any) -> tuple[str | None, bool]:
        """
        Retourne (iso_date|None, ambiguous).
        Date ambiguë (03/04/2026) → requires_review, ne choisit pas silencieusement.
        """
        if raw is None or raw == "":
            return None, False
        s = str(raw).strip()
        m = _ISO_DATE.match(s)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", False
        m = _FR_DATE.match(s)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if d > 12:
                return f"{y:04d}-{mo:02d}-{d:02d}", False
            if mo > 12:
                return f"{y:04d}-{d:02d}-{mo:02d}", False
            # les deux <= 12 → ambigu
            return None, True
        if _AMBIGUOUS_DATE.match(s):
            return None, True
        raise ValueError("invalid_date")

    def normalize_integer(self, raw: Any) -> int | None:
        if raw is None or raw == "":
            return None
        if isinstance(raw, bool):
            raise ValueError("invalid_integer")
        if isinstance(raw, int):
            return raw
        s = str(raw).strip().replace(" ", "")
        if not re.fullmatch(r"-?\d+", s):
            raise ValueError("invalid_integer")
        return int(s)

    def normalize_boolean(self, raw: Any) -> bool | None:
        if raw is None or raw == "":
            return None
        if isinstance(raw, bool):
            return raw
        s = str(raw).strip().lower()
        if s in ("true", "1", "oui", "yes", "y"):
            return True
        if s in ("false", "0", "non", "no", "n"):
            return False
        raise ValueError("invalid_boolean")

    def extract_amounts_from_text(self, text: str, *, limit: int = 20) -> list[Decimal]:
        out: list[Decimal] = []
        for m in _AMOUNT_RE.finditer(text or ""):
            try:
                out.append(self.normalize_decimal(m.group(1)))
            except ValueError:
                continue
            if len(out) >= limit:
                break
        return out
