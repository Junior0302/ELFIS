"""Deterministic structured diff between proposal versions."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def _money(v: Any) -> Decimal:
    return Decimal(str(v or 0))


def compare_versions(
    *,
    from_version: dict[str, Any],
    to_version: dict[str, Any],
    from_lines: list[dict[str, Any]],
    to_lines: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare structured data — not PDFs, not AI."""
    from_map = {str(l.get("source_key") or l.get("name") or l["id"]): l for l in from_lines}
    to_map = {str(l.get("source_key") or l.get("name") or l["id"]): l for l in to_lines}

    added, removed, modified = [], [], []
    for key, line in to_map.items():
        if key not in from_map:
            added.append({"key": key, "after": line})
        else:
            prev = from_map[key]
            fields = []
            for field in ("quantity", "unit_price", "discount_type", "discount_value", "tax_rate", "total"):
                if str(prev.get(field)) != str(line.get(field)):
                    fields.append({"field": field, "before": prev.get(field), "after": line.get(field)})
            if fields:
                modified.append({"key": key, "changes": fields, "before": prev, "after": line})
    for key, line in from_map.items():
        if key not in to_map:
            removed.append({"key": key, "before": line})

    meta_changes = []
    for field in ("valid_until", "terms", "payment_terms", "notes", "title", "introduction", "scope"):
        if str(from_version.get(field) or "") != str(to_version.get(field) or ""):
            meta_changes.append(
                {"field": field, "before": from_version.get(field), "after": to_version.get(field)}
            )

    total_delta = _money(to_version.get("total")) - _money(from_version.get("total"))
    return {
        "from_version": from_version.get("version_number"),
        "to_version": to_version.get("version_number"),
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "total_delta": str(total_delta),
            "meta_changed": len(meta_changes),
        },
        "changes": {
            "lines_added": added,
            "lines_removed": removed,
            "lines_modified": modified,
            "meta": meta_changes,
        },
    }
