"""Usage et estimation de coûts — registry centralisé (pas de prix inventés)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class ModelPricing:
    provider: str
    model: str
    input_cost_per_million: Decimal
    output_cost_per_million: Decimal
    effective_from: str  # ISO date


# Tarifs connus uniquement — si modèle absent → estimated_cost = null
_PRICING: tuple[ModelPricing, ...] = (
    ModelPricing(
        provider="openai",
        model="gpt-4o-mini",
        input_cost_per_million=Decimal("0.15"),
        output_cost_per_million=Decimal("0.60"),
        effective_from="2024-07-18",
    ),
)


def get_pricing(provider: str, model: str) -> ModelPricing | None:
    provider = (provider or "").strip().lower()
    model = (model or "").strip()
    for row in _PRICING:
        if row.provider == provider and row.model == model:
            return row
    return None


def estimate_cost(
    *,
    provider: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> Optional[Decimal]:
    pricing = get_pricing(provider, model)
    if pricing is None:
        return None
    inp = Decimal(input_tokens or 0)
    out = Decimal(output_tokens or 0)
    cost = (inp / Decimal(1_000_000)) * pricing.input_cost_per_million + (
        out / Decimal(1_000_000)
    ) * pricing.output_cost_per_million
    return cost.quantize(Decimal("0.000001"))
