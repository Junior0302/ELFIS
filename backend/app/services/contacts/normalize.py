from __future__ import annotations

import re
import unicodedata

_LEGAL_FORMS = (
    "sasu",
    "sas",
    "sarl",
    "eurl",
    "sa",
    "sci",
    "scp",
    "sca",
    "scs",
    "snc",
    "selarl",
    "ei",
    "eirl",
    "auto entrepreneur",
    "auto-entrepreneur",
)


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def digits_only(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")


def normalize_company_name(value: str) -> str:
    """Minuscules, sans accents/ponctuation, formes juridiques retirées."""
    text = strip_accents(value or "").lower()
    # Formes pointées (S.A.S., S.A.R.L., …) avant retrait de la ponctuation
    for pattern in (
        r"\bs\.?\s*a\.?\s*s\.?\s*u\.?\b",
        r"\bs\.?\s*a\.?\s*s\.?\b",
        r"\bs\.?\s*a\.?\s*r\.?\s*l\.?\b",
        r"\be\.?\s*u\.?\s*r\.?\s*l\.?\b",
        r"\bs\.?\s*c\.?\s*i\.?\b",
        r"\bs\.?\s*a\.?\b",
        r"\be\.?\s*i\.?\b",
    ):
        text = re.sub(pattern, " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = text.split()
    cleaned = [t for t in tokens if t not in _LEGAL_FORMS]
    return " ".join(cleaned).strip()


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def normalize_vat(value: str | None) -> str:
    return re.sub(r"[\s.]+", "", (value or "").upper())
