"""Types normalisés — réponses structurées, outils, explainability, actions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class FeedbackKind(str, Enum):
    useful = "useful"
    useless = "useless"
    incorrect = "incorrect"


class ProposedAction(BaseModel):
    """Action proposée — les modifications restent soumises à confirmation."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    href: str
    requires_confirmation: bool = False
    description: str = ""


class Explanation(BaseModel):
    """Explainability d'une recommandation."""

    model_config = ConfigDict(extra="forbid")

    why: str
    data_used: list[str] = Field(default_factory=list)
    calculation: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    data_as_of: datetime | None = None


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    explanation: Explanation
    action: ProposedAction | None = None


class StructuredAnswer(BaseModel):
    """Réponse à 4 sections obligatoires — aucune invention de données."""

    model_config = ConfigDict(extra="forbid")

    facts: list[str] = Field(default_factory=list)
    estimates: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    summary: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    sources: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    actions: list[ProposedAction] = Field(default_factory=list)
    data_as_of: datetime | None = None

    def to_plain_text(self) -> str:
        """Rendu lisible pour le chat et l'historique legacy."""
        parts: list[str] = []
        if self.summary:
            parts.append(self.summary)
        if self.facts:
            parts.append("Faits vérifiés :")
            parts.extend(f"• {f}" for f in self.facts)
        if self.estimates:
            parts.append("Estimations :")
            parts.extend(f"• {e}" for e in self.estimates)
        if self.recommendations:
            parts.append("Recommandations :")
            for r in self.recommendations:
                parts.append(f"• {r.text}")
                parts.append(
                    f"  Pourquoi ? {r.explanation.why} "
                    f"(confiance : {r.explanation.confidence.value})"
                )
        if self.missing:
            parts.append("Informations manquantes :")
            parts.extend(f"• {m}" for m in self.missing)
        return "\n".join(parts).strip()


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool: str
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    data_as_of: datetime | None = None


class AssistantRunMetrics(BaseModel):
    latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    llm_called: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    tools_called: list[str] = Field(default_factory=list)
    cache_hit: bool = False
    error: str | None = None
