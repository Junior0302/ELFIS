"""Routes HTTP Document Analysis — /api/document-analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.document_analysis.exceptions import (
    DocumentAnalysisConflictError,
    DocumentAnalysisError,
    DocumentAnalysisNotFoundError,
    DocumentAnalysisValidationError,
)
from app.document_analysis.schemas import (
    AnalysisReportListOut,
    AnalysisReportOut,
    AnalyzeBatchOut,
    AnalyzeItemIn,
)
from app.document_analysis.service import DocumentAnalysisService

router = APIRouter(
    prefix="/document-analysis",
    tags=["document-analysis"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> DocumentAnalysisService:
    return DocumentAnalysisService(db)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, DocumentAnalysisNotFoundError):
        return HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentAnalysisConflictError):
        return HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentAnalysisValidationError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentAnalysisError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    return HTTPException(
        status_code=400,
        detail={"code": "document_analysis_error", "message": "Erreur analyse"},
    )


@router.post(
    "/items/{item_id}/analyze",
    response_model=AnalysisReportOut,
    status_code=201,
)
def analyze_item(
    item_id: str,
    body: AnalyzeItemIn | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_analysis.run")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).analyze_item(
            item_id,
            org_id,
            actor_user_id=auth.user_id,
            force=bool(body.force) if body else False,
        )
        return AnalysisReportOut.from_orm_report(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.post(
    "/sessions/{migration_session_id}/analyze",
    response_model=AnalyzeBatchOut,
    status_code=201,
)
def analyze_session(
    migration_session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_analysis.run")
    org_id = auth.require_organization_id()
    try:
        result = _svc(db).analyze_migration_session(
            organization_id=org_id,
            migration_session_id=migration_session_id,
            actor_user_id=auth.user_id,
        )
        return AnalyzeBatchOut(
            analyzed=result["analyzed"],
            errors=result["errors"],
            items=[AnalysisReportOut.from_orm_report(r) for r in result["reports"]],
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/reports/{report_id}", response_model=AnalysisReportOut)
def get_report(
    report_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_analysis.read")
    org_id = auth.require_organization_id()
    try:
        return AnalysisReportOut.from_orm_report(_svc(db).get_report(report_id, org_id))
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/items/{item_id}/report", response_model=AnalysisReportOut)
def get_item_report(
    item_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_analysis.read")
    org_id = auth.require_organization_id()
    try:
        return AnalysisReportOut.from_orm_report(
            _svc(db).get_latest_for_item(item_id, org_id)
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/sessions/{migration_session_id}/reports", response_model=AnalysisReportListOut)
def list_session_reports(
    migration_session_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("document_analysis.read")
    org_id = auth.require_organization_id()
    rows, total = _svc(db).list_for_session(
        organization_id=org_id,
        migration_session_id=migration_session_id,
        limit=limit,
        offset=offset,
    )
    return AnalysisReportListOut(
        items=[AnalysisReportOut.from_orm_report(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
