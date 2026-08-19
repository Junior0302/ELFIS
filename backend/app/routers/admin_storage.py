"""API admin read-only — Storage provider / migrations / integrity (RC2.4 étape 4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.storage.storage_integrity_service import StorageIntegrityService
from app.storage.storage_migration_service import StorageMigrationService
from app.storage.storage_registry import get_provider_info

router = APIRouter(prefix="/admin/storage", tags=["admin-storage"])


class ProviderInfoOut(BaseModel):
    configured_provider: str
    active_provider: str
    capabilities: dict
    download_mode: str
    supabase_bucket_configured: bool
    supabase_url_configured: bool


class MigrationOut(BaseModel):
    id: str
    storage_object_id: str
    source_provider: str
    target_provider: str
    status: str
    checksum_verified: bool
    error_code: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    model_config = {"from_attributes": True}


class MigrationListOut(BaseModel):
    items: list[MigrationOut]
    total: int


class IntegritySummaryOut(BaseModel):
    scanned: int
    ok: int
    failed: int
    mode: str
    preview: bool


@router.get("/provider", response_model=ProviderInfoOut)
def get_provider(auth: AuthContext = Depends(get_auth_context)):
    auth.require_any(["storage.providers.read", "storage.objects.read", "system.health.read", "*"])
    info = get_provider_info()
    return ProviderInfoOut(**info)


@router.get("/migrations", response_model=MigrationListOut)
def list_migrations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require_any(["storage.migrations.read", "*"])
    items, total = StorageMigrationService(db).list_migrations(
        status=status, limit=limit, offset=offset
    )
    out = []
    for m in items:
        out.append(
            MigrationOut(
                id=m.id,
                storage_object_id=m.storage_object_id,
                source_provider=m.source_provider,
                target_provider=m.target_provider,
                status=m.status,
                checksum_verified=bool(m.checksum_verified),
                error_code=m.error_code,
                started_at=m.started_at.isoformat() if m.started_at else None,
                completed_at=m.completed_at.isoformat() if m.completed_at else None,
            )
        )
    return MigrationListOut(items=out, total=total)


@router.get("/migrations/{migration_id}", response_model=MigrationOut)
def get_migration(
    migration_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require_any(["storage.migrations.read", "*"])
    m = StorageMigrationService(db).get(migration_id)
    if not m:
        raise HTTPException(404, detail={"code": "not_found", "message": "Migration introuvable"})
    return MigrationOut(
        id=m.id,
        storage_object_id=m.storage_object_id,
        source_provider=m.source_provider,
        target_provider=m.target_provider,
        status=m.status,
        checksum_verified=bool(m.checksum_verified),
        error_code=m.error_code,
        started_at=m.started_at.isoformat() if m.started_at else None,
        completed_at=m.completed_at.isoformat() if m.completed_at else None,
    )


@router.get("/integrity-summary", response_model=IntegritySummaryOut)
def integrity_summary(
    provider: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require_any(["storage.integrity.read", "*"])
    report = StorageIntegrityService(db).verify(
        provider=provider, limit=limit, full_checksum=False, preview=True
    )
    return IntegritySummaryOut(
        scanned=report.scanned,
        ok=report.ok,
        failed=report.failed,
        mode=report.mode,
        preview=report.preview,
    )
