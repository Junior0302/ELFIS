"""Routes utilisateur — consultation / annulation limitée des jobs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.jobs import bootstrap_job_handlers
from app.jobs.job_exceptions import JobNotFoundError, JobValidationError
from app.jobs.job_service import JobService

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(require_active_subscription)],
)


@router.get("/{job_id}")
def get_job_status(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    bootstrap_job_handlers()
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    svc = JobService(db)
    try:
        job = svc.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(404, detail="Job introuvable") from None
    if not svc.user_can_access(job, organization_id=org_id, user_id=auth.user.id):
        raise HTTPException(404, detail="Job introuvable")
    return svc.to_user_view(job).model_dump()


@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    bootstrap_job_handlers()
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    svc = JobService(db)
    try:
        job = svc.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(404, detail="Job introuvable") from None
    if job.organization_id != org_id or job.user_id != auth.user.id:
        raise HTTPException(404, detail="Job introuvable")
    try:
        job = svc.cancel_job(job_id, actor_user_id=auth.user.id)
    except JobValidationError as exc:
        raise HTTPException(400, detail=exc.message) from None
    return svc.to_user_view(job).model_dump()
