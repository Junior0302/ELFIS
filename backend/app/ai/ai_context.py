"""Contexte d'exécution IA (handlers / tâches)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AIContext:
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    correlation_id: Optional[str] = None
    job_id: Optional[str] = None
    execution_id: Optional[str] = None
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    extra: dict[str, Any] = field(default_factory=dict)
