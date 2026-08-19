"""Édition contrôlée des champs — non destructive."""

from __future__ import annotations

from typing import Any


def set_path(data: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Retourne une copie avec le chemin mis à jour."""
    out = _deepcopy_dict(data)
    parts = path.split(".")
    cur: Any = out
    for p in parts[:-1]:
        if not isinstance(cur.get(p), dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value
    return out


def get_path(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for p in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def flatten_fields(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (data or {}).items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and k not in ("line_items", "transactions", "taxes", "parties"):
            out.update(flatten_fields(v, path))
        else:
            out[path] = v
    return out


def _deepcopy_dict(d: dict[str, Any]) -> dict[str, Any]:
    import copy

    return copy.deepcopy(d)
