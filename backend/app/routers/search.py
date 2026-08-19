"""Routes Search Engine — utilisateur + plateforme."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin
from app.jobs import bootstrap_job_handlers
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames
from app.models_saas import User
from app.search.search_exceptions import (
    SearchDisabledError,
    SearchNotFoundError,
    SearchValidationError,
)
from app.search.search_registry import bootstrap_indexers
from app.search.search_repository import SearchRepository
from app.search.search_schemas import SearchQuery
from app.search.search_security import assert_page_size, filter_metadata
from app.search.search_service import SearchService
from app.search.search_types import SearchResourceTypes
import uuid

router = APIRouter(prefix="/search", tags=["search"])
platform_router = APIRouter(
    prefix="/platform/search",
    tags=["platform-search"],
    dependencies=[Depends(require_platform_admin)],
)


def _svc(db: Session) -> SearchService:
    bootstrap_indexers()
    return SearchService(db)


@router.get("", dependencies=[Depends(require_active_subscription)])
def search(
    q: str | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    category: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    currency: str | None = None,
    requires_review: bool | None = None,
    sort: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    org_id = auth.require_organization_id()
    from app.billing.billing_guards import require_feature
    from app.billing.billing_types import FeatureCodes

    require_feature(db, org_id, FeatureCodes.SEARCH_GLOBAL, user=auth.user)
    types = [resource_type] if resource_type else None
    statuses = [status] if status else None
    categories = [category] if category else None
    try:
        result = _svc(db).search(
            organization_id=org_id,
            query=SearchQuery(
                query=q,
                resource_types=types,
                statuses=statuses,
                categories=categories,
                date_from=date_from,
                date_to=date_to,
                amount_min=amount_min,
                amount_max=amount_max,
                currency=currency,
                requires_review=requires_review,
                page=page,
                page_size=page_size or 20,
                sort=sort,
            ),
        )
    except SearchDisabledError as exc:
        raise HTTPException(503, detail=exc.message) from None
    except SearchValidationError as exc:
        raise HTTPException(400, detail=exc.message) from None
    return result.model_dump()


@router.get("/suggestions", dependencies=[Depends(require_active_subscription)])
def suggestions(
    q: str = Query("", min_length=0),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    org_id = auth.require_organization_id()
    try:
        items = _svc(db).suggest(organization_id=org_id, query=q, limit=limit)
    except SearchValidationError as exc:
        raise HTTPException(400, detail=exc.message) from None
    return {"suggestions": [i.model_dump() for i in items]}


@platform_router.get("/documents")
def platform_list_documents(
    organization_id: int | None = None,
    resource_type: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    rows, total = SearchRepository(db).list_platform(
        organization_id=organization_id,
        resource_type=resource_type,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "documents": [
            {
                "search_document_id": r.search_document_id,
                "organization_id": r.organization_id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "title": r.title,
                "status": r.status,
                "is_active": r.is_active,
                "indexed_at": r.indexed_at,
            }
            for r in rows
        ],
    }


@platform_router.get("/documents/{search_document_id}")
def platform_get_document(
    search_document_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    try:
        row = _svc(db).get_search_document(search_document_id=search_document_id)
    except SearchNotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    return {
        "search_document_id": row.search_document_id,
        "organization_id": row.organization_id,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "title": row.title,
        "subtitle": row.subtitle,
        "status": row.status,
        "category": row.category,
        "amount": float(row.amount) if row.amount is not None else None,
        "currency": row.currency,
        "action_url": row.action_url,
        "metadata": filter_metadata(row.metadata_json if isinstance(row.metadata_json, dict) else {}),
        "is_active": row.is_active,
        "indexed_at": row.indexed_at,
        # jamais search_text complet côté plateforme liste détail — preview limitée
        "content_preview": (row.content or row.search_text or "")[:500],
    }


@platform_router.post("/reindex")
def platform_reindex_all(
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    """Enqueue réindexation — organization_id requis via body query."""
    raise HTTPException(400, detail="Utiliser POST /reindex/{organization_id}")


@platform_router.post("/reindex/{organization_id}")
def platform_reindex_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    bootstrap_job_handlers()
    bootstrap_indexers()
    job = JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.SEARCH_REINDEX_ORGANIZATION,
            organization_id=organization_id,
            user_id=admin.id,
            payload={"organization_id": organization_id},
            idempotency_key=f"search-reindex-org:{organization_id}:{uuid.uuid4()}",
            correlation_id=str(uuid.uuid4()),
        )
    )
    return {"job_id": job.job_id, "organization_id": organization_id, "status": "pending"}


@platform_router.delete("/documents/{search_document_id}")
def platform_soft_delete(
    search_document_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    _ = admin
    try:
        row = _svc(db).get_search_document(search_document_id=search_document_id)
        result = _svc(db).remove_resource(
            organization_id=row.organization_id,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            resource_version=row.resource_version,
        )
    except SearchNotFoundError as exc:
        raise HTTPException(404, detail=exc.message) from None
    return result.model_dump()
