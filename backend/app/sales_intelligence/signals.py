"""Insight draft dataclass produced by rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InsightDraft:
    insight_type: str
    category: str
    severity: str
    priority_score: int
    title: str
    summary: str
    explanation: dict[str, Any]
    evidence: list[dict[str, Any]]
    source_type: str
    source_id: str | None
    source_label: str | None
    deduplication_key: str
    route: str | None
    recommended_action: dict[str, Any]
    available_actions: list[dict[str, Any]]
    resolution_condition: str
    observed_value: str | None = None
    score: int | None = None
    project_decision: bool = False
    notify: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
