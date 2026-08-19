"""Provenance / preuves — jamais de longs extraits texte."""

from __future__ import annotations

from typing import Any

from app.document_processing.extraction.provider import FieldEvidence


def evidence_to_safe_dict(ev: FieldEvidence) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if ev.page is not None:
        out["page"] = int(ev.page)
    if ev.rule:
        out["rule"] = str(ev.rule)[:64]
    if ev.evidence_code:
        out["evidence_code"] = str(ev.evidence_code)[:64]
    if ev.method:
        out["method"] = str(ev.method)[:32]
    return out


def truncate_evidence_list(items: list[FieldEvidence] | None, *, limit: int = 5) -> list[dict[str, Any]]:
    if not items:
        return []
    return [evidence_to_safe_dict(e) for e in items[:limit]]
