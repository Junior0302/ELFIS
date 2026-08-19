"""Routes HTTP Validation & Mapping — /api/validation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.validation_mapping.exceptions import (
    ValidationConflictError,
    ValidationMappingError,
    ValidationNotFoundError,
    ValidationStateError,
)
from app.validation_mapping.schemas import (
    BatchStartOut,
    DuplicateListOut,
    DuplicateOut,
    FieldEditIn,
    HistoryEntryOut,
    HistoryListOut,
    MatchListOut,
    MatchOut,
    RejectIn,
    ResolveMatchIn,
    ValidateIn,
    ValidationFieldOut,
    ValidationFieldsOut,
    ValidationSessionListOut,
    ValidationSessionOut,
)
from app.validation_mapping.service import ValidationMappingService

router = APIRouter(
    prefix="/validation",
    tags=["validation-mapping"],
    dependencies=[Depends(require_active_subscription)],
)


def _svc(db: Session) -> ValidationMappingService:
    return ValidationMappingService(db)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, ValidationNotFoundError):
        return HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, (ValidationConflictError, ValidationStateError)):
        return HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, ValidationMappingError):
        return HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})
    return HTTPException(
        status_code=400,
        detail={"code": "validation_error", "message": "Erreur validation"},
    )


@router.post(
    "/sessions/{migration_session_id}/start",
    response_model=BatchStartOut,
    status_code=201,
)
def start_batch(
    migration_session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.edit")
    org_id = auth.require_organization_id()
    try:
        result = _svc(db).start_session_batch(
            organization_id=org_id,
            migration_session_id=migration_session_id,
            actor_user_id=auth.user_id,
        )
        return BatchStartOut(
            started=result["started"],
            errors=result["errors"],
            items=[ValidationSessionOut.from_orm_row(r) for r in result["items"]],
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get(
    "/sessions/{migration_session_id}/items",
    response_model=ValidationSessionListOut,
)
def list_sessions(
    migration_session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.read")
    org_id = auth.require_organization_id()
    rows = _svc(db).list_for_migration(
        organization_id=org_id, migration_session_id=migration_session_id
    )
    return ValidationSessionListOut(
        items=[ValidationSessionOut.from_orm_row(r) for r in rows],
        total=len(rows),
    )


@router.post("/documents/{document_id}/start", response_model=ValidationSessionOut, status_code=201)
def start_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.edit")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).start_or_get(
            document_id, org_id, actor_user_id=auth.user_id
        )
        return ValidationSessionOut.from_orm_row(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/documents/{document_id}", response_model=ValidationSessionOut)
def get_document_validation(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.read")
    org_id = auth.require_organization_id()
    try:
        return ValidationSessionOut.from_orm_row(
            _svc(db).get_for_document(document_id, org_id)
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/{session_id}", response_model=ValidationSessionOut)
def get_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.read")
    org_id = auth.require_organization_id()
    try:
        return ValidationSessionOut.from_orm_row(_svc(db).get_session(session_id, org_id))
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/{session_id}/fields", response_model=ValidationFieldsOut)
def get_fields(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.read")
    org_id = auth.require_organization_id()
    try:
        rows = _svc(db).list_fields(session_id, org_id)
        return ValidationFieldsOut(
            fields=[
                ValidationFieldOut(
                    field_path=r.field_path,
                    ai_value=r.ai_value,
                    current_value=r.current_value,
                    status=r.status,
                    confidence=r.confidence,
                    provenance=dict(r.provenance or {}),
                    warnings=list(r.warnings_json or []),
                )
                for r in rows
            ]
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.patch("/{session_id}/fields/{field_path:path}", response_model=ValidationFieldOut)
def patch_field(
    session_id: str,
    field_path: str,
    body: FieldEditIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.edit")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).edit_field(
            session_id,
            org_id,
            field_path=field_path,
            new_value=body.value,
            actor_user_id=auth.user_id,
            reason=body.reason,
            action=body.action or "edit",
        )
        return ValidationFieldOut(
            field_path=row.field_path,
            ai_value=row.ai_value,
            current_value=row.current_value,
            status=row.status,
            confidence=row.confidence,
            provenance=dict(row.provenance or {}),
            warnings=list(row.warnings_json or []),
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/{session_id}/validate", response_model=ValidationSessionOut)
def validate_document(
    session_id: str,
    body: ValidateIn | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.validate")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).validate_document(
            session_id,
            org_id,
            actor_user_id=auth.user_id,
            mark_ready=True if body is None else body.mark_ready,
        )
        return ValidationSessionOut.from_orm_row(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/{session_id}/reject", response_model=ValidationSessionOut)
def reject_document(
    session_id: str,
    body: RejectIn | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.reject")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).reject_document(
            session_id,
            org_id,
            actor_user_id=auth.user_id,
            reason=body.reason if body else None,
        )
        return ValidationSessionOut.from_orm_row(row)
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/{session_id}/history", response_model=HistoryListOut)
def get_history(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.history")
    org_id = auth.require_organization_id()
    try:
        rows = _svc(db).get_history(session_id, org_id)
        return HistoryListOut(
            items=[
                HistoryEntryOut(
                    id=r.id,
                    field_path=r.field_path,
                    old_value=r.old_value,
                    new_value=r.new_value,
                    action=r.action,
                    reason=r.reason,
                    actor_user_id=r.actor_user_id,
                    created_at=r.created_at,
                )
                for r in rows
            ]
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/{session_id}/duplicates", response_model=DuplicateListOut)
def get_duplicates(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.read")
    org_id = auth.require_organization_id()
    try:
        rows = _svc(db).get_duplicates(session_id, org_id)
        return DuplicateListOut(
            items=[
                DuplicateOut(
                    id=r.id,
                    other_document_id=r.other_document_id,
                    other_universal_document_id=r.other_universal_document_id,
                    severity=r.severity,
                    score=r.score,
                    matched_fields=list(r.matched_fields or []),
                    explanation=r.explanation,
                    resolution=r.resolution,
                )
                for r in rows
            ]
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/{session_id}/matching", response_model=MatchListOut)
def get_matching(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.match")
    org_id = auth.require_organization_id()
    try:
        rows = _svc(db).get_matches(session_id, org_id)
        return MatchListOut(
            items=[
                MatchOut(
                    id=r.id,
                    party_role=r.party_role,
                    category=r.category,
                    score=r.score,
                    contact_id=r.contact_id,
                    contact_label=r.contact_label,
                    matched_criteria=list(r.matched_criteria or []),
                    explanation=r.explanation,
                    resolution=r.resolution,
                )
                for r in rows
            ]
        )
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/matches/{match_id}/resolve", response_model=MatchOut)
def resolve_match(
    match_id: str,
    body: ResolveMatchIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("validation.match")
    org_id = auth.require_organization_id()
    try:
        row = _svc(db).resolve_match(
            match_id,
            org_id,
            resolution=body.resolution,
            actor_user_id=auth.user_id,
        )
        return MatchOut(
            id=row.id,
            party_role=row.party_role,
            category=row.category,
            score=row.score,
            contact_id=row.contact_id,
            contact_label=row.contact_label,
            matched_criteria=list(row.matched_criteria or []),
            explanation=row.explanation,
            resolution=row.resolution,
        )
    except Exception as exc:
        raise _http(exc) from exc
