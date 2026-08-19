"""API Accounting Intelligence V2 — /api/accounting/intelligence."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.accounting_intelligence.exceptions import (
    AccountingIntelligenceError,
    IntelligenceNotFoundError,
    IntelligenceStateError,
    IntelligenceValidationError,
)
from app.accounting_intelligence.schemas import (
    FeedbackIn,
    IntelligenceOut,
    RecommendQuery,
    RetrainIn,
    SimilarityIn,
)
from app.accounting_intelligence.service import IntelligenceService
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription

router = APIRouter(
    prefix="/accounting/intelligence",
    tags=["accounting-intelligence-v2"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> IntelligenceService:
    return IntelligenceService(db)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, IntelligenceNotFoundError):
        return HTTPException(
            status_code=404, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, (IntelligenceStateError, IntelligenceValidationError)):
        return HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, AccountingIntelligenceError):
        return HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        )
    return HTTPException(
        status_code=400,
        detail={
            "code": "accounting_intelligence_error",
            "message": "Erreur intelligence comptable",
        },
    )


@router.get("/recommendations", response_model=IntelligenceOut)
def get_recommendations(
    recommendation_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    payload_json: str | None = Query(
        None, description="JSON payload optionnel pour générer une reco"
    ),
    proposal_id: str | None = Query(None),
    generate: bool = Query(False),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Liste ou génère des recommandations (GET recommendations)."""
    auth.require("accounting_intelligence.read")
    org_id = auth.require_organization_id()
    try:
        svc = _svc(db)
        if recommendation_id:
            return IntelligenceOut(
                data=svc.get_recommendation(
                    organization_id=org_id, recommendation_id=recommendation_id
                )
            )
        if payload_json or proposal_id or generate:
            payload = json.loads(payload_json) if payload_json else {}
            return IntelligenceOut(
                data=svc.recommend(
                    organization_id=org_id,
                    actor_user_id=auth.user_id,
                    payload=payload,
                    proposal_id=proposal_id,
                    generate_proposal=generate,
                )
            )
        return IntelligenceOut(
            data={"items": svc.list_recommendations(organization_id=org_id, limit=limit)}
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/recommendations", response_model=IntelligenceOut, status_code=201)
def post_recommendations(
    body: RecommendQuery,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Génère une recommandation (corps JSON)."""
    auth.require("accounting_intelligence.read")
    org_id = auth.require_organization_id()
    try:
        return IntelligenceOut(
            data=_svc(db).recommend(
                organization_id=org_id,
                actor_user_id=auth.user_id,
                payload=body.payload,
                proposal_id=body.proposal_id,
                generate_proposal=body.generate_proposal,
            )
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/explanations", response_model=IntelligenceOut)
def get_explanations(
    recommendation_id: str | None = Query(None),
    proposal_id: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_intelligence.read")
    org_id = auth.require_organization_id()
    try:
        return IntelligenceOut(
            data=_svc(db).explanations(
                organization_id=org_id,
                recommendation_id=recommendation_id,
                proposal_id=proposal_id,
            )
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/learning", response_model=IntelligenceOut)
def get_learning(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_intelligence.read")
    org_id = auth.require_organization_id()
    try:
        return IntelligenceOut(data=_svc(db).learning_state(organization_id=org_id))
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/feedback", response_model=IntelligenceOut, status_code=201)
def post_feedback(
    body: FeedbackIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_intelligence.feedback")
    org_id = auth.require_organization_id()
    try:
        return IntelligenceOut(
            data=_svc(db).submit_feedback(
                organization_id=org_id,
                actor_user_id=auth.user_id,
                action=body.action,
                recommendation_id=body.recommendation_id,
                proposal_id=body.proposal_id,
                validation_seconds=body.validation_seconds,
                comment=body.comment,
                modifications=body.modifications,
                cancelled=body.cancelled,
                import_rejected=body.import_rejected,
            )
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/retrain", response_model=IntelligenceOut)
def post_retrain(
    body: RetrainIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_intelligence.retrain")
    org_id = auth.require_organization_id()
    try:
        data = _svc(db).retrain(
            organization_id=org_id, actor_user_id=auth.user_id
        )
        if body.note:
            data["note"] = body.note
        return IntelligenceOut(data=data)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/similarity", response_model=IntelligenceOut)
def get_similarity(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
    supplier_name: str | None = Query(None),
    customer_name: str | None = Query(None),
    direction: str | None = Query(None),
    document_type: str | None = Query(None),
    amount_ttc: float | None = Query(None),
    vat_rate: float | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
):
    auth.require("accounting_intelligence.read")
    org_id = auth.require_organization_id()
    payload = {
        k: v
        for k, v in {
            "supplier_name": supplier_name,
            "customer_name": customer_name,
            "direction": direction,
            "document_type": document_type,
            "amount_ttc": amount_ttc,
            "vat_rate": vat_rate,
        }.items()
        if v is not None
    }
    try:
        return IntelligenceOut(
            data=_svc(db).similarity(
                organization_id=org_id, payload=payload, limit=limit
            )
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/similarity", response_model=IntelligenceOut)
def post_similarity(
    body: SimilarityIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_intelligence.read")
    org_id = auth.require_organization_id()
    try:
        return IntelligenceOut(
            data=_svc(db).similarity(
                organization_id=org_id, payload=body.payload, limit=body.limit
            )
        )
    except Exception as exc:
        raise _http(exc) from exc
