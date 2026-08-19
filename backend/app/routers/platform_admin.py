"""Routes Platform Admin V1 — agrégation + opérations (ne remplace pas /api/platform existant)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_platform_admin
from app.models_saas import User
from app.platform_admin.admin_exceptions import AdminError
from app.platform_admin.admin_schemas import AdminActionIn, AdminIncidentNoteIn
from app.platform_admin.admin_service import AdminService
from app.config import settings

router = APIRouter(
    prefix="/platform",
    tags=["platform-admin-ops"],
    dependencies=[Depends(require_platform_admin)],
)


def _http(exc: AdminError) -> HTTPException:
    code = 400
    if exc.code == "not_found":
        code = 404
    elif exc.code in ("platform_admin_required", "action_denied", "permission_denied"):
        code = 403
    return HTTPException(status_code=code, detail={"code": exc.code, "message": exc.message})


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/dashboard")
def platform_dashboard(
    period: str = Query("24h"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    if not getattr(settings, "elfis_platform_admin_enabled", True):
        raise HTTPException(503, detail={"code": "platform_admin_disabled", "message": "Admin désactivé"})
    return AdminService(db).dashboard.get_dashboard(period=period)


@router.get("/health/services")
def platform_health_services(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    return AdminService(db).health.check_all()


@router.get("/organizations/{organization_id}/ops-detail")
def platform_admin_organization_ops_detail(
    organization_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    """Détail agrégé ops (complète GET /organizations/{id} existant)."""
    try:
        return AdminService(db).organizations.get_organization_detail(organization_id)
    except AdminError as exc:
        raise _http(exc) from exc


@router.post("/organizations/{organization_id}/suspend")
def platform_admin_suspend_organization(
    organization_id: int,
    payload: AdminActionIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        org = AdminService(db).organizations.suspend(
            organization_id, actor=admin, reason=payload.reason, ip=_ip(request)
        )
        db.commit()
        return {"ok": True, "organization_id": org.id, "platform_status": org.platform_status}
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/organizations/{organization_id}/restore")
def platform_admin_restore_organization(
    organization_id: int,
    payload: AdminActionIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        org = AdminService(db).organizations.restore(
            organization_id, actor=admin, reason=payload.reason, ip=_ip(request)
        )
        db.commit()
        return {"ok": True, "organization_id": org.id, "platform_status": org.platform_status}
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/users/{user_id}/disable")
def platform_admin_disable_user(
    user_id: int,
    payload: AdminActionIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        user = AdminService(db).operations.disable_user(
            user_id, actor=admin, reason=payload.reason, ip=_ip(request)
        )
        db.commit()
        return {"ok": True, "user_id": user.id, "status": user.status}
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/users/{user_id}/enable")
def platform_admin_enable_user(
    user_id: int,
    payload: AdminActionIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        user = AdminService(db).operations.enable_user(
            user_id, actor=admin, reason=payload.reason, ip=_ip(request)
        )
        db.commit()
        return {"ok": True, "user_id": user.id, "status": user.status}
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/jobs/{job_id}/manual-retry")
def platform_admin_retry_job(
    job_id: str,
    payload: AdminActionIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    """Retry audité avec raison (complète POST /jobs/{id}/retry)."""
    try:
        result = AdminService(db).operations.retry_job(
            job_id, actor=admin, reason=payload.reason, ip=_ip(request)
        )
        db.commit()
        return result
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(400, detail={"code": "job_retry_failed", "message": str(exc)}) from exc


@router.post("/jobs/{job_id}/manual-cancel")
def platform_admin_cancel_job_with_reason(
    job_id: str,
    payload: AdminActionIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        result = AdminService(db).operations.cancel_job(
            job_id, actor=admin, reason=payload.reason, ip=_ip(request)
        )
        db.commit()
        return result
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(400, detail={"code": "job_cancel_failed", "message": str(exc)}) from exc


@router.post("/events/{event_id}/retry")
def platform_admin_retry_event(
    event_id: str,
    payload: AdminActionIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        result = AdminService(db).operations.retry_event(
            event_id, actor=admin, reason=payload.reason, ip=_ip(request)
        )
        db.commit()
        return result
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/events/{event_id}/mark-resolved")
def platform_admin_mark_event_resolved(
    event_id: str,
    payload: AdminActionIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        result = AdminService(db).operations.mark_event_resolved(
            event_id, actor=admin, reason=payload.reason, ip=_ip(request)
        )
        db.commit()
        return result
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.get("/vault-documents")
def platform_admin_list_documents(
    organization_id: int | None = None,
    page: int = 1,
    page_size: int | None = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    return AdminService(db).operations.list_documents(
        organization_id=organization_id, page=page, page_size=page_size
    )


@router.get("/vault-documents/{vault_document_id}")
def platform_admin_document_detail(
    vault_document_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    try:
        return AdminService(db).operations.get_document_aggregate(vault_document_id)
    except AdminError as exc:
        raise _http(exc) from exc


@router.get("/incidents")
def platform_admin_list_incidents(
    organization_id: int | None = None,
    status: str | None = None,
    incident_type: str | None = None,
    page: int = 1,
    page_size: int | None = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    if not getattr(settings, "elfis_platform_incidents_enabled", True):
        return {"incidents": [], "total": 0, "page": 1, "page_size": 25}
    svc = AdminService(db)
    svc.incidents.scan_dead_letters()
    db.commit()
    return svc.incidents.list_incidents(
        organization_id=organization_id,
        status=status,
        incident_type=incident_type,
        page=page,
        page_size=page_size,
    )


@router.get("/incidents/{incident_id}")
def platform_admin_get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    try:
        return AdminService(db).incidents.get_incident(incident_id)
    except AdminError as exc:
        raise _http(exc) from exc


@router.post("/incidents/{incident_id}/acknowledge")
def platform_admin_ack_incident(
    incident_id: str,
    payload: AdminIncidentNoteIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        result = AdminService(db).incidents.acknowledge(
            incident_id, actor=admin, note=payload.note, ip=_ip(request)
        )
        db.commit()
        return result
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/incidents/{incident_id}/resolve")
def platform_admin_resolve_incident(
    incident_id: str,
    payload: AdminIncidentNoteIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        result = AdminService(db).incidents.resolve(
            incident_id, actor=admin, note=payload.note, ip=_ip(request)
        )
        db.commit()
        return result
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/incidents/{incident_id}/ignore")
def platform_admin_ignore_incident(
    incident_id: str,
    payload: AdminIncidentNoteIn,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        result = AdminService(db).incidents.ignore(
            incident_id, actor=admin, note=payload.note, ip=_ip(request)
        )
        db.commit()
        return result
    except AdminError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.get("/global-search")
def platform_admin_global_search(
    q: str = Query(..., min_length=2, max_length=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    try:
        return AdminService(db).operations.global_search(q)
    except AdminError as exc:
        raise _http(exc) from exc


@router.get("/audit")
def platform_admin_list_audit(
    actor_user_id: int | None = None,
    organization_id: int | None = None,
    action: str | None = None,
    target_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int | None = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
):
    from app.platform_admin.admin_security import clamp_page, clamp_page_size

    page_n = clamp_page(page)
    size = clamp_page_size(page_size)
    rows, total = AdminService(db).audit.list_audits(
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        action=action,
        target_type=target_type,
        status=status,
        page=page_n,
        page_size=size,
    )
    return {
        "audits": [
            {
                "audit_id": r.audit_id,
                "actor_user_id": r.actor_user_id,
                "actor_email": r.actor_email,
                "organization_id": r.organization_id,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "reason": r.reason,
                "previous_state": r.previous_state,
                "new_state": r.new_state,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "total": total,
        "page": page_n,
        "page_size": size,
    }
