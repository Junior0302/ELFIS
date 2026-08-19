"""API Accounting Engine V2 — endpoints sous /api/accounting."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.accounting_engine.exceptions import (
    AccountingEngineError,
    EngineNotFoundError,
    EngineStateError,
    EngineValidationError,
)
from app.accounting_engine.proposal_service import ProposalService
from app.accounting_engine.schemas import (
    ConfidenceOut,
    ExplanationOut,
    GenerateIn,
    ProposalOut,
    RegenerateIn,
)

router = APIRouter(
    prefix="/accounting",
    tags=["accounting-engine-v2"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> ProposalService:
    return ProposalService(db)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, EngineNotFoundError):
        return HTTPException(
            status_code=404, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, (EngineStateError, EngineValidationError)):
        return HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        )
    if isinstance(exc, AccountingEngineError):
        return HTTPException(
            status_code=400, detail={"code": exc.code, "message": exc.message}
        )
    return HTTPException(
        status_code=400,
        detail={"code": "accounting_engine_error", "message": "Erreur moteur comptable"},
    )


@router.get("/proposal", response_model=ProposalOut)
def get_proposal(
    proposal_id: str = Query(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_engine.read")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).get_proposal(organization_id=org_id, proposal_id=proposal_id)
        return ProposalOut(data=_svc(db).to_dict(row))
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/generate", response_model=ProposalOut, status_code=201)
def generate_proposal(
    body: GenerateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_engine.generate")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).generate(
            organization_id=org_id,
            actor_user_id=auth.user_id,
            payload=body.payload,
            invoice_id=body.invoice_id,
            source_document_id=body.source_document_id,
            source_kind=body.source_kind,
        )
        return ProposalOut(data=_svc(db).to_dict(row))
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/regenerate", response_model=ProposalOut)
def regenerate_proposal(
    body: RegenerateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_engine.regenerate")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).regenerate(
            organization_id=org_id,
            proposal_id=body.proposal_id,
            actor_user_id=auth.user_id,
            payload_overrides=body.payload_overrides,
        )
        return ProposalOut(data=_svc(db).to_dict(row))
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/confidence", response_model=ConfidenceOut)
def get_confidence(
    proposal_id: str = Query(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_engine.read")
    org_id = auth.require_organization_id()
    try:
        data = _svc(db).confidence(organization_id=org_id, proposal_id=proposal_id)
        return ConfidenceOut(**data)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/explanation", response_model=ExplanationOut)
def get_explanation(
    proposal_id: str = Query(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("accounting_engine.read")
    org_id = auth.require_organization_id()
    try:
        data = _svc(db).explanation(organization_id=org_id, proposal_id=proposal_id)
        return ExplanationOut(data=data)
    except Exception as exc:
        raise _http(exc) from exc
