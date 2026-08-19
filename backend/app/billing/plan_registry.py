"""Registre central des plans Billing V2.

Identifiants Stripe uniquement via settings / variables d'environnement —
jamais de price_id inventés ni transmis par le frontend.
Les montants catalogue sont indicatifs pour MRR/UI ; le prix facturé = Stripe Price.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.billing.billing_types import (
    BillingIntervals,
    FeatureCodes,
    PlanCodes,
    QuotaCodes,
)


@dataclass(frozen=True)
class PlanDefinition:
    plan_code: str
    name: str
    description: str
    currency: str
    billing_interval: str
    price_amount: Decimal
    trial_days: int
    is_active: bool
    is_public: bool
    purchasable: bool
    features: dict[str, bool] = field(default_factory=dict)
    quotas: dict[str, int | None] = field(default_factory=dict)
    stripe_price_env: str | None = None  # nom de settings, ex. stripe_price_starter_monthly


# Features starter — valeurs préparatoires (ajustables via DB/admin)
STARTER_FEATURES: dict[str, bool] = {
    FeatureCodes.DOCUMENTS_UPLOAD: True,
    FeatureCodes.DOCUMENTS_VAULT: True,
    FeatureCodes.DOCUMENTS_TEXT_EXTRACTION: True,
    FeatureCodes.DOCUMENTS_OCR: False,
    FeatureCodes.AI_CLASSIFICATION: True,
    FeatureCodes.AI_INVOICE_EXTRACTION: True,
    FeatureCodes.AI_QUALITY_CHECK: True,
    FeatureCodes.ACCOUNTING_PROPOSALS: True,
    FeatureCodes.ACCOUNTING_VALIDATION: True,
    FeatureCodes.ACCOUNTING_EXPORT: False,
    FeatureCodes.SEARCH_GLOBAL: True,
    FeatureCodes.EMAIL_SEND: True,
    FeatureCodes.NOTIFICATIONS_IN_APP: True,
    FeatureCodes.PLATFORM_CUSTOM_EMAIL: False,
    FeatureCodes.USERS_MULTI_USER: False,
    FeatureCodes.ORGANIZATIONS_MULTI_ENTITY: False,
    FeatureCodes.API_ACCESS: False,
}

# Quotas préparatoires : None = illimité (pas de hard block silencieux)
STARTER_QUOTAS: dict[str, int | None] = {
    QuotaCodes.DOCUMENTS_PROCESSED_MONTH: None,
    QuotaCodes.AI_EXECUTIONS_MONTH: None,
    QuotaCodes.AI_TOKENS_MONTH: None,
    QuotaCodes.EMAILS_SENT_MONTH: None,
    QuotaCodes.STORAGE_BYTES: None,
    QuotaCodes.ORGANIZATION_USERS: 1,
}

TRIAL_FEATURES = {**STARTER_FEATURES}
TRIAL_QUOTAS = {**STARTER_QUOTAS}


def _build_registry() -> dict[str, PlanDefinition]:
    return {
        PlanCodes.FREE_TRIAL: PlanDefinition(
            plan_code=PlanCodes.FREE_TRIAL,
            name="Essai gratuit",
            description="Essai 14 jours — mêmes fonctionnalités que Starter.",
            currency="EUR",
            billing_interval=BillingIntervals.NONE,
            price_amount=Decimal("0"),
            trial_days=14,
            is_active=True,
            is_public=False,
            purchasable=False,
            features=deepcopy(TRIAL_FEATURES),
            quotas=deepcopy(TRIAL_QUOTAS),
            stripe_price_env=None,
        ),
        PlanCodes.STARTER: PlanDefinition(
            plan_code=PlanCodes.STARTER,
            name="Starter",
            description="ComptaPilot IA — 19 €/mois. Essai 14 jours puis renouvellement automatique.",
            currency="EUR",
            billing_interval=BillingIntervals.MONTH,
            price_amount=Decimal("19.00"),
            trial_days=14,
            is_active=True,
            is_public=True,
            purchasable=True,
            features=deepcopy(STARTER_FEATURES),
            quotas=deepcopy(STARTER_QUOTAS),
            # Alias : STRIPE_PRICE_STARTER_MONTHLY ou legacy STRIPE_PRICE_PRO
            stripe_price_env="stripe_price_starter_monthly",
        ),
        PlanCodes.PROFESSIONAL: PlanDefinition(
            plan_code=PlanCodes.PROFESSIONAL,
            name="Professional",
            description="Multi-utilisateurs, OCR, exports comptables — prix via Stripe env.",
            currency="EUR",
            billing_interval=BillingIntervals.MONTH,
            price_amount=Decimal("49.00"),  # catalogue affichage ; Stripe price_id via env
            trial_days=14,
            is_active=True,
            is_public=True,
            purchasable=True,
            features={
                **STARTER_FEATURES,
                FeatureCodes.DOCUMENTS_OCR: True,
                FeatureCodes.ACCOUNTING_EXPORT: True,
                FeatureCodes.USERS_MULTI_USER: True,
            },
            quotas={
                **STARTER_QUOTAS,
                QuotaCodes.ORGANIZATION_USERS: 10,
                QuotaCodes.DOCUMENTS_PROCESSED_MONTH: 500,
                QuotaCodes.AI_EXECUTIONS_MONTH: 1000,
            },
            stripe_price_env="stripe_price_professional_monthly",
        ),
        PlanCodes.ENTERPRISE: PlanDefinition(
            plan_code=PlanCodes.ENTERPRISE,
            name="Enterprise",
            description="API, multi-entités, quotas sur mesure — commercial.",
            currency="EUR",
            billing_interval=BillingIntervals.MONTH,
            price_amount=Decimal("0"),  # sur devis — jamais de price inventé côté client
            trial_days=0,
            is_active=True,
            is_public=False,
            purchasable=False,
            features={
                **STARTER_FEATURES,
                FeatureCodes.DOCUMENTS_OCR: True,
                FeatureCodes.ACCOUNTING_EXPORT: True,
                FeatureCodes.USERS_MULTI_USER: True,
                FeatureCodes.ORGANIZATIONS_MULTI_ENTITY: True,
                FeatureCodes.API_ACCESS: True,
            },
            quotas={**STARTER_QUOTAS, QuotaCodes.ORGANIZATION_USERS: None},
            stripe_price_env="stripe_price_enterprise_monthly",
        ),
    }


_PLAN_REGISTRY: dict[str, PlanDefinition] = _build_registry()


def get_plan(plan_code: str) -> PlanDefinition | None:
    return _PLAN_REGISTRY.get((plan_code or "").strip().lower())


def list_plans(*, public_only: bool = False, active_only: bool = True) -> list[PlanDefinition]:
    rows = list(_PLAN_REGISTRY.values())
    if active_only:
        rows = [p for p in rows if p.is_active]
    if public_only:
        rows = [p for p in rows if p.is_public]
    return rows


def resolve_stripe_price_id(plan_code: str) -> str | None:
    """Résout le price_id Stripe depuis la config — jamais depuis le client."""
    from app.config import settings

    plan = get_plan(plan_code)
    if not plan or not plan.purchasable:
        return None
    # Starter : nouveau nom puis legacy STRIPE_PRICE_PRO
    if plan.plan_code == PlanCodes.STARTER:
        price = (settings.stripe_price_starter_monthly or settings.stripe_price_pro or "").strip()
        return price or None
    if plan.stripe_price_env:
        price = (getattr(settings, plan.stripe_price_env, "") or "").strip()
        return price or None
    return None


def plan_code_for_stripe_price(price_id: str | None) -> str | None:
    if not price_id:
        return None
    pid = price_id.strip()
    for code in (PlanCodes.STARTER, PlanCodes.PROFESSIONAL, PlanCodes.ENTERPRISE):
        resolved = resolve_stripe_price_id(code)
        if resolved and resolved == pid:
            return code
    # Legacy : tout price_pro connu = starter
    from app.config import settings

    if settings.stripe_price_pro and settings.stripe_price_pro.strip() == pid:
        return PlanCodes.STARTER
    return None


def default_plan_code() -> str:
    from app.config import settings

    code = (settings.elfis_default_plan_code or PlanCodes.STARTER).strip().lower()
    return code if get_plan(code) else PlanCodes.STARTER


def plan_to_public_dict(plan: PlanDefinition, *, include_stripe: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "plan_code": plan.plan_code,
        "name": plan.name,
        "description": plan.description,
        "currency": plan.currency,
        "billing_interval": plan.billing_interval,
        "price_amount": float(plan.price_amount),
        "trial_days": plan.trial_days,
        "is_active": plan.is_active,
        "is_public": plan.is_public,
        "purchasable": plan.purchasable and bool(resolve_stripe_price_id(plan.plan_code)),
        "features": dict(plan.features),
        "quotas": dict(plan.quotas),
    }
    if include_stripe:
        data["stripe_price_configured"] = bool(resolve_stripe_price_id(plan.plan_code))
    return data
