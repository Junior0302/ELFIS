"""API admin — lecture, recherche avancée, statistiques, export audit."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from app.audit.audit_dependencies import (
    get_audit_service,
    require_audit_export,
    require_audit_read,
)
from app.audit.audit_export import AuditExportService
from app.audit.audit_filters import AuditEventFilters
from app.audit.audit_models import ElfisAuditEvent
from app.audit.audit_sanitize import sanitize_metadata
from app.audit.audit_service import AuditService
from app.config import settings
from app.database import get_db
from app.iam.permission_context import PermissionContext
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    occurred_at: datetime
    severity: str
    category: str
    action: str
    status: str
    actor_user_id: int | None = None
    actor_email: str | None = None
    organization_id: int | None = None
    product: str | None = None
    service: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    target_display: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    message: str | None = None
    duration_ms: int | None = None
    success: bool
    metadata: dict | None = None


class AuditEventListOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuditEventOut]


class AuditStatisticsOut(BaseModel):
    since: str
    hours: int = 24
    total: int
    success: int
    failure: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    by_action: dict[str, int]
    by_service: dict[str, int] = {}
    by_day: dict[str, int] = {}
    permission_denied: int = 0
    login_failure: int = 0
    iam_changes: int = 0
    warnings_errors: int = 0


def _to_out(row: ElfisAuditEvent) -> AuditEventOut:
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else None
    return AuditEventOut(
        id=row.id,
        occurred_at=row.occurred_at,
        severity=row.severity,
        category=row.category,
        action=row.action,
        status=row.status,
        actor_user_id=row.actor_user_id,
        actor_email=row.actor_email,
        organization_id=row.organization_id,
        product=row.product,
        service=row.service,
        target_type=row.target_type,
        target_id=row.target_id,
        target_display=row.target_display,
        request_id=row.request_id,
        correlation_id=row.correlation_id,
        ip_address=row.ip_address,
        user_agent=row.user_agent,
        message=row.message,
        duration_ms=row.duration_ms,
        success=row.success,
        metadata=sanitize_metadata(meta) if meta else None,
    )


def _build_filters(
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    hours: int | None,
    severity: str | None,
    category: str | None,
    actor_user_id: int | None,
    actor_email: str | None,
    organization_id: int | None,
    service: str | None,
    product: str | None,
    action: str | None,
    status: str | None,
    success: bool | None,
    target_type: str | None = None,
    target_id: str | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
    q: str | None = None,
    sort: str = "occurred_at_desc",
    limit: int = 25,
    offset: int = 0,
    max_range_days: int | None = None,
) -> AuditEventFilters:
    resolved_from = date_from
    if resolved_from is None and hours is not None:
        resolved_from = datetime.utcnow() - timedelta(hours=hours)
    filters = AuditEventFilters(
        date_from=resolved_from,
        date_to=date_to,
        severity=severity,
        category=category,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        organization_id=organization_id,
        service=service,
        product=product,
        action=action,
        status=status,
        success=success,
        target_type=target_type,
        target_id=target_id,
        correlation_id=correlation_id,
        request_id=request_id,
        q=q,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    err = filters.validate_enums()
    if err:
        raise HTTPException(422, detail={"code": err, "message": "Filtre invalide"})
    err = filters.validate_date_range(max_days=max_range_days)
    if err:
        raise HTTPException(422, detail={"code": err, "message": "Plage de dates invalide"})
    return filters


@router.get("/events", response_model=AuditEventListOut)
def list_audit_events(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    hours: int | None = Query(default=None, ge=1, le=720),
    severity: str | None = Query(default=None, max_length=32),
    category: str | None = Query(default=None, max_length=32),
    actor_user_id: int | None = Query(default=None),
    actor_email: str | None = Query(default=None, max_length=255),
    organization_id: int | None = Query(default=None),
    service: str | None = Query(default=None, max_length=128),
    product: str | None = Query(default=None, max_length=128),
    action: str | None = Query(default=None, max_length=128),
    status: str | None = Query(default=None, max_length=32),
    success: bool | None = Query(default=None),
    target_type: str | None = Query(default=None, max_length=64),
    target_id: str | None = Query(default=None, max_length=128),
    correlation_id: str | None = Query(default=None, max_length=64),
    request_id: str | None = Query(default=None, max_length=64),
    q: str | None = Query(default=None, max_length=64),
    sort: str = Query(default="occurred_at_desc", max_length=32),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _ctx: PermissionContext = Depends(require_audit_read),
    svc: AuditService = Depends(get_audit_service),
) -> AuditEventListOut:
    filters = _build_filters(
        date_from=date_from,
        date_to=date_to,
        hours=hours,
        severity=severity,
        category=category,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        organization_id=organization_id,
        service=service,
        product=product,
        action=action,
        status=status,
        success=success,
        target_type=target_type,
        target_id=target_id,
        correlation_id=correlation_id,
        request_id=request_id,
        q=q,
        sort=sort,
        limit=limit,
        offset=offset,
        max_range_days=int(settings.audit_search_max_range_days),
    )
    items = svc.list_events(filters)
    total = svc.count_events(filters)
    return AuditEventListOut(
        total=total,
        limit=filters.limit,
        offset=filters.offset,
        items=[_to_out(r) for r in items],
    )


@router.get("/events/{event_id}", response_model=AuditEventOut)
def get_audit_event(
    event_id: str = Path(min_length=8, max_length=36),
    _ctx: PermissionContext = Depends(require_audit_read),
    svc: AuditService = Depends(get_audit_service),
) -> AuditEventOut:
    row = svc.get_event(event_id)
    if not row:
        raise HTTPException(
            404,
            detail={"code": "audit_event_not_found", "message": "Événement introuvable"},
        )
    return _to_out(row)


@router.get("/statistics", response_model=AuditStatisticsOut)
def audit_statistics(
    hours: int = Query(default=24, ge=1, le=720),
    _ctx: PermissionContext = Depends(require_audit_read),
    svc: AuditService = Depends(get_audit_service),
) -> AuditStatisticsOut:
    stats = svc.statistics(hours=hours)
    return AuditStatisticsOut(**stats)


@router.get("/export")
def export_audit_events(
    format: str = Query(default="csv", pattern=r"^(csv|jsonl)$"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    hours: int | None = Query(default=None, ge=1, le=720),
    severity: str | None = Query(default=None, max_length=32),
    category: str | None = Query(default=None, max_length=32),
    actor_user_id: int | None = Query(default=None),
    actor_email: str | None = Query(default=None, max_length=255),
    organization_id: int | None = Query(default=None),
    service: str | None = Query(default=None, max_length=128),
    product: str | None = Query(default=None, max_length=128),
    action: str | None = Query(default=None, max_length=128),
    status: str | None = Query(default=None, max_length=32),
    success: bool | None = Query(default=None),
    target_type: str | None = Query(default=None, max_length=64),
    target_id: str | None = Query(default=None, max_length=128),
    correlation_id: str | None = Query(default=None, max_length=64),
    request_id: str | None = Query(default=None, max_length=64),
    q: str | None = Query(default=None, max_length=64),
    sort: str = Query(default="occurred_at_desc", max_length=32),
    ctx: PermissionContext = Depends(require_audit_export),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    filters = _build_filters(
        date_from=date_from,
        date_to=date_to,
        hours=hours,
        severity=severity,
        category=category,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        organization_id=organization_id,
        service=service,
        product=product,
        action=action,
        status=status,
        success=success,
        target_type=target_type,
        target_id=target_id,
        correlation_id=correlation_id,
        request_id=request_id,
        q=q,
        sort=sort,
        limit=25,
        offset=0,
        max_range_days=int(settings.audit_export_max_range_days),
    )
    exporter = AuditExportService(db)
    err = exporter.validate_export_filters(filters)
    if err:
        raise HTTPException(422, detail={"code": err, "message": "Export refusé — filtres hors limites"})

    # Pré-vérifier le volume
    total = AuditService(db, isolated_writes=False).count_events(filters)
    max_rows = int(settings.audit_export_max_rows)
    if total > max_rows:
        raise HTTPException(
            422,
            detail={
                "code": "export_too_large",
                "message": f"Trop de résultats ({total}). Maximum {max_rows}. Affinez les filtres.",
                "total": total,
                "max_rows": max_rows,
            },
        )

    actor_id = ctx.user_id
    if format == "jsonl":
        gen = exporter.export_jsonl_chunks(filters, actor_user_id=actor_id)
        media = "application/x-ndjson; charset=utf-8"
        filename = "audit-export.jsonl"
    else:
        gen = exporter.export_csv_chunks(filters, actor_user_id=actor_id)
        media = "text/csv; charset=utf-8"
        filename = "audit-export.csv"

    return StreamingResponse(
        gen,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
