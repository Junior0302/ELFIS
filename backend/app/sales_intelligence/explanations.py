"""Explanation + evidence helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def explanation(
    *,
    headline: str,
    observed_facts: list[str],
    rule_applied: str,
    why_it_matters: str,
    recommended_next_step: str,
    resolution_condition: str,
) -> dict[str, Any]:
    return {
        "headline": headline,
        "observed_facts": observed_facts,
        "rule_applied": rule_applied,
        "why_it_matters": why_it_matters,
        "recommended_next_step": recommended_next_step,
        "resolution_condition": resolution_condition,
    }


def evidence_item(
    *,
    type: str,
    label: str,
    value: Any = None,
    description: str | None = None,
    source: str | None = None,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "type": type,
        "label": label,
        "value": value if value is None or isinstance(value, (str, int, float)) else str(value),
        "description": description,
        "source": source,
        "observed_at": observed_at.isoformat() if isinstance(observed_at, datetime) else observed_at,
    }
