"""Guards métier — EntitlementService / QuotaService (pas de Stripe dans les routes)."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.billing.billing_exceptions import FeatureNotAvailableError, QuotaExceededError
from app.billing.entitlement_service import EntitlementService
from app.billing.quota_service import QuotaService
from app.config import settings


def require_feature(
    db: Session,
    organization_id: int,
    feature_code: str,
    *,
    user=None,
) -> None:
    if not getattr(settings, "elfis_billing_enabled", True):
        return
    if not getattr(settings, "elfis_billing_enforce_entitlements", True):
        return
    try:
        EntitlementService(db).require(organization_id, feature_code, user=user)
    except FeatureNotAvailableError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "feature_not_available",
                "message": "Cette fonctionnalité n’est pas disponible avec votre offre actuelle.",
                "feature_code": exc.feature_code,
            },
        ) from exc


def check_and_consume_quota(
    db: Session,
    organization_id: int,
    quota_code: str,
    amount: int = 1,
) -> None:
    if not getattr(settings, "elfis_billing_enabled", True):
        return
    if not getattr(settings, "elfis_billing_enforce_quotas", False):
        # Observation : enregistre quand même si limite définie? non — consume seulement si enforce
        return
    try:
        QuotaService(db).consume(organization_id, quota_code, amount)
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "quota_exceeded",
                "message": "La limite d’utilisation a été atteinte.",
                "quota_code": exc.quota_code,
            },
        ) from exc
