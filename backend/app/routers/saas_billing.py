"""Routes SaaS Billing — coexistent avec /api/billing (facturation commerciale).

Endpoints :
  GET  /api/billing/plans
  GET  /api/billing/subscription
  ...
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.billing.billing_exceptions import BillingError, FeatureNotAvailableError, QuotaExceededError
from app.billing.billing_schemas import CheckoutRequest
from app.billing.billing_service import BillingService
from app.config import settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.subscriptions.consent import record_checkout_consent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing-saas"])


def _http_from_billing(exc: BillingError) -> HTTPException:
    status = 400
    if isinstance(exc, FeatureNotAvailableError):
        status = 403
    elif isinstance(exc, QuotaExceededError):
        status = 429
    elif exc.code == "not_found":
        status = 404
    elif exc.code == "permission_denied":
        status = 403
    return HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message})


@router.get("/overview")
def get_billing_overview(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Billing System V2 — état org via Entitlement Engine."""
    organization_id = auth.require_organization_id()
    return BillingService(db).org_overview(organization_id, user=auth.user)


@router.get("/plans")
def list_billing_plans(db: Session = Depends(get_db)):
    return {"plans": BillingService(db).list_public_plans()}


@router.get("/subscription")
def get_billing_subscription(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    organization_id = auth.require_organization_id()
    return BillingService(db).get_subscription(organization_id, user=auth.user)


@router.get("/entitlements")
def get_billing_entitlements(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    organization_id = auth.require_organization_id()
    return {"entitlements": BillingService(db).get_entitlements(organization_id)}


@router.get("/usage")
def get_billing_usage(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    organization_id = auth.require_organization_id()
    return {"usage": BillingService(db).get_usage(organization_id)}


@router.get("/quotas")
def get_billing_quotas(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    organization_id = auth.require_organization_id()
    return {"quotas": BillingService(db).get_quotas(organization_id)}


@router.get("/history")
def get_billing_history(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    organization_id = auth.require_organization_id()
    return {"events": BillingService(db).billing_history(organization_id)}


@router.get("/webhooks")
def get_billing_webhooks_audit(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Journal des événements webhook traités (idempotents) — pas de secrets Stripe."""
    organization_id = auth.require_organization_id()
    return {
        "events": BillingService(db).billing_history(organization_id, limit=50),
        "ingest": {
            "primary": "/api/subscriptions/webhook",
            "alias": "/api/webhooks/stripe",
            "note": "Réception signée Stripe ; source de vérité = Billing Engine.",
        },
    }


@router.post("/checkout")
def billing_checkout(
    request: Request,
    payload: CheckoutRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    record_checkout_consent(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
        automatic_renewal_accepted=payload.automatic_renewal_accepted,
        terms_accepted=payload.terms_accepted,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    try:
        result = BillingService(db).checkout(
            organization_id=organization_id,
            user_email=auth.user.email,
            plan_code=payload.plan_code or settings.elfis_default_plan_code,
            automatic_renewal_accepted=payload.automatic_renewal_accepted,
            terms_accepted=payload.terms_accepted,
        )
        db.commit()
        return result if isinstance(result, dict) else {"url": result}
    except BillingError as exc:
        db.rollback()
        raise _http_from_billing(exc) from exc
    except HTTPException:
        db.rollback()
        raise


@router.post("/customer-portal")
def billing_customer_portal(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()
    try:
        return BillingService(db).customer_portal(organization_id)
    except BillingError as exc:
        raise _http_from_billing(exc) from exc
    except HTTPException:
        raise


@router.post("/cancel")
def billing_cancel(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """V1 : ouvre le portail Stripe (annulation fin de période)."""
    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()
    try:
        return BillingService(db).stripe.cancel_subscription(organization_id, at_period_end=True)
    except BillingError as exc:
        raise _http_from_billing(exc) from exc
    except HTTPException:
        raise


@router.post("/resume")
def billing_resume(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()
    try:
        return BillingService(db).stripe.resume_subscription(organization_id)
    except BillingError as exc:
        raise _http_from_billing(exc) from exc
    except HTTPException:
        raise
