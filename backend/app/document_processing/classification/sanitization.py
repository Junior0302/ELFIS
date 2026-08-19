"""Sanitisation preuves / raisons — jamais de filename complet ni contenu."""

from __future__ import annotations

import re
from typing import Any

_MAX_EVIDENCE = 20
_MAX_REASON = 255
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def sanitize_reason(reason: str | None) -> str | None:
    if not reason:
        return None
    text = _EMAIL_RE.sub("[redacted]", str(reason).strip())
    return text[:_MAX_REASON] or None


def sanitize_evidence_items(items: list[dict[str, Any]] | None, *, max_items: int = _MAX_EVIDENCE) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or item.get("signal") or "").strip()[:64]
        if not code:
            continue
        detail = item.get("detail")
        clean: dict[str, Any] = {"code": code}
        if detail is not None:
            d = str(detail)[:80]
            d = _EMAIL_RE.sub("[redacted]", d)
            # jamais de filename brut
            if "filename" in code.lower() and ("/" in d or "\\" in d):
                continue
            clean["detail"] = d
        weight = item.get("weight")
        if isinstance(weight, (int, float)):
            clean["weight"] = round(float(weight), 4)
        out.append(clean)
        if len(out) >= max_items:
            break
    return out


def round_score(score: float) -> float:
    return max(0.0, min(1.0, round(float(score), 4)))
