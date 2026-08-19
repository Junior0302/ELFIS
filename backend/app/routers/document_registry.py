"""API Document Registry — upload streaming + download sécurisé (RC2.4 étape 2)."""

from __future__ import annotations

import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.audit.audit_logger import AuditLogger
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.storage.document_access_policy import DocumentAccessPolicy
from app.storage.document_legal_hold_service import DocumentLegalHoldService
from app.storage.document_registry_service import DocumentRegistryService
from app.storage.storage_exceptions import (
    DocumentAccessDeniedError,
    DocumentNotFoundError,
    StorageDisabledError,
    StorageError,
    StorageNotFoundError,
    StorageValidationError,
)
from app.storage.storage_repository import DocumentVersionRepository, LegalHoldRepository
from app.storage.storage_schemas import (
    DocumentDeleteBody,
    DocumentLinkCreate,
    DocumentLinkOut,
    DocumentListOut,
    DocumentRecordOut,
    DocumentVersionListOut,
    DocumentVersionOut,
    LegalHoldCreate,
    LegalHoldListOut,
    LegalHoldOut,
    StorageObjectOut,
)
from app.storage.storage_upload import iter_upload_file_chunks

router = APIRouter(
    prefix="/document-registry",
    tags=["document-registry"],
    dependencies=[Depends(require_active_subscription)],
)

_policy = DocumentAccessPolicy()


def _svc(db: Session) -> DocumentRegistryService:
    return DocumentRegistryService(db, audit_logger=AuditLogger(db), access_policy=_policy)


def _http_from_storage(exc: StorageError) -> HTTPException:
    if isinstance(exc, StorageValidationError):
        return HTTPException(400, detail={"code": exc.code, "message": exc.message})
    if isinstance(exc, DocumentAccessDeniedError):
        if exc.code == "permission_denied":
            return HTTPException(
                403,
                detail={"code": "permission_denied", "message": exc.message},
            )
        return HTTPException(404, detail={"code": "not_found", "message": "Document introuvable"})
    if isinstance(exc, (DocumentNotFoundError, StorageNotFoundError)):
        return HTTPException(404, detail={"code": "not_found", "message": "Document introuvable"})
    if isinstance(exc, StorageDisabledError):
        return HTTPException(503, detail={"code": exc.code, "message": "Stockage indisponible"})
    return HTTPException(500, detail={"code": "storage_error", "message": "Erreur stockage"})


def _content_disposition(filename: str, *, inline: bool = False) -> str:
    safe = "".join(
        c if 32 <= ord(c) < 127 and c not in {'"', "\\", "\r", "\n"} else "_" for c in (filename or "download")
    )
    disposition = "inline" if inline else "attachment"
    return f"{disposition}; filename=\"{safe}\"; filename*=UTF-8''{quote(filename or 'download')}"


def _serialize_doc(svc: DocumentRegistryService, doc, *, duplicate: bool | None = None) -> DocumentRecordOut:
    obj = svc.get_storage_object(doc)
    storage_out = StorageObjectOut.model_validate(obj) if obj else None
    meta = dict(doc.metadata_json or {})
    if duplicate is not None:
        meta["duplicate_candidate"] = duplicate
    version_count = None
    legal_hold_active = None
    try:
        version_count = len(DocumentVersionRepository(svc._db).list_for_document(doc.id))
        legal_hold_active = LegalHoldRepository(svc._db).has_active(doc.id)
    except Exception:
        pass
    return DocumentRecordOut(
        id=doc.id,
        document_type=doc.document_type,
        title=doc.title,
        status=doc.status,
        organization_id=doc.organization_id,
        product=doc.product,
        current_storage_object_id=doc.current_storage_object_id,
        current_version_id=getattr(doc, "current_version_id", None),
        version_count=version_count,
        owner_user_id=doc.owner_user_id,
        source=doc.source,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        archived_at=doc.archived_at,
        deleted_at=getattr(doc, "deleted_at", None),
        legal_hold_active=legal_hold_active,
        storage_object=storage_out,
        metadata_json=meta or None,
    )


def _serialize_version(ver) -> DocumentVersionOut:
    return DocumentVersionOut.model_validate(ver)


def _parse_metadata(raw: str | None) -> dict | None:
    if not raw or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            400, detail={"code": "METADATA_INVALID", "message": "metadata JSON invalide"}
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            400, detail={"code": "METADATA_INVALID", "message": "metadata doit être un objet"}
        )
    return data


def _parse_links(raw: str | None) -> list[dict[str, str]] | None:
    if not raw or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, detail={"code": "METADATA_INVALID", "message": "links JSON invalide"}) from exc
    if not isinstance(data, list):
        raise HTTPException(400, detail={"code": "METADATA_INVALID", "message": "links doit être une liste"})
    return data[:20]


async def _do_upload(
    *,
    file: UploadFile,
    title: str | None,
    document_type: str,
    product: str | None,
    source: str,
    metadata_raw: str | None,
    links_raw: str | None,
    auth: AuthContext,
    db: Session,
) -> DocumentRecordOut:
    _policy.assert_can_create(auth)
    org_id = _policy.resolve_organization_id(auth)
    if not file.filename:
        raise HTTPException(400, detail={"code": "INVALID_FILENAME", "message": "Fichier manquant"})
    meta = _parse_metadata(metadata_raw)
    links = _parse_links(links_raw)
    svc = _svc(db)
    try:
        doc, duplicate = await svc.create_from_stream(
            organization_id=org_id,
            filename=file.filename,
            chunk_iterator=iter_upload_file_chunks(file),
            declared_mime=file.content_type,
            title=title,
            document_type=document_type,
            product=product,
            source=source,
            owner_user_id=auth.user.id if auth.user else None,
            metadata=meta,
            links=links,
        )
    except DocumentAccessDeniedError as exc:
        raise _http_from_storage(exc) from exc
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _serialize_doc(svc, doc, duplicate=duplicate)


@router.post("/upload", response_model=DocumentRecordOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    document_type: str = Form(default="file"),
    product: str | None = Form(default=None),
    source: str = Form(default="upload"),
    metadata: str | None = Form(default=None),
    links: str | None = Form(default=None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    return await _do_upload(
        file=file,
        title=title,
        document_type=document_type,
        product=product,
        source=source,
        metadata_raw=metadata,
        links_raw=links,
        auth=auth,
        db=db,
    )


@router.post("", response_model=DocumentRecordOut, status_code=201)
async def create_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    document_type: str = Form(default="file"),
    product: str | None = Form(default=None),
    source: str = Form(default="upload"),
    metadata: str | None = Form(default=None),
    links: str | None = Form(default=None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Alias compat — même pipeline streaming que /upload."""
    return await _do_upload(
        file=file,
        title=title,
        document_type=document_type,
        product=product,
        source=source,
        metadata_raw=metadata,
        links_raw=links,
        auth=auth,
        db=db,
    )


@router.get("", response_model=DocumentListOut)
def list_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_archived: bool = Query(False),
    document_type: str | None = Query(None),
    source: str | None = Query(None),
    status: str | None = Query(None),
    product: str | None = Query(None),
    filename: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    items, total = svc.list_for_organization(
        org_id,
        include_archived=include_archived,
        document_type=document_type,
        source=source,
        status=status,
        product=product,
        filename_contains=filename,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )
    return DocumentListOut(
        items=[_serialize_doc(svc, d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentRecordOut)
def get_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_read(auth, doc)
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _serialize_doc(svc, doc)


def _download_response(
    *,
    svc: DocumentRegistryService,
    doc,
    obj,
    inline: bool,
    allow_quarantine: bool = False,
) -> StreamingResponse:
    try:
        stream = svc.open_download(doc, allow_quarantine=allow_quarantine)
    except StorageError:
        raise
    filename = obj.safe_filename or "download"
    media = obj.mime_type_detected or obj.mime_type_declared or "application/octet-stream"
    headers = {
        "Content-Disposition": _content_disposition(filename, inline=inline),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    }
    if obj.size_bytes and int(obj.size_bytes) > 0:
        headers["Content-Length"] = str(int(obj.size_bytes))

    def _iter():
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            try:
                stream.close()
            except Exception:
                pass

    return StreamingResponse(_iter(), media_type=media, headers=headers)


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    audit = AuditLogger(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        obj = svc.get_storage_object(doc)
        audit.record_document_download_requested(
            document_id=doc.id,
            organization_id=org_id,
            actor_user_id=auth.user.id if auth.user else None,
        )
        _policy.assert_can_download(auth, doc, obj)
        assert obj is not None
        allow_q = obj.status == "quarantined"
    except DocumentAccessDeniedError as exc:
        audit.record_document_download_denied(
            document_id=document_id,
            organization_id=org_id,
            actor_user_id=auth.user.id if auth.user else None,
            reason=exc.code,
        )
        raise _http_from_storage(exc) from exc
    except StorageError as exc:
        raise _http_from_storage(exc) from exc

    audit.record_document_downloaded(
        document_id=doc.id,
        storage_object_id=obj.id,
        organization_id=org_id,
        actor_user_id=auth.user.id if auth.user else None,
        size_bytes=obj.size_bytes,
        mime=obj.mime_type_detected or obj.mime_type_declared,
    )
    return _download_response(svc=svc, doc=doc, obj=obj, inline=False, allow_quarantine=allow_q)


@router.get("/{document_id}/content")
def preview_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Prévisualisation inline limitée (PDF / images)."""
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        obj = svc.get_storage_object(doc)
        _policy.assert_can_download(auth, doc, obj)
        assert obj is not None
        mime = obj.mime_type_detected or obj.mime_type_declared
        if not _policy.can_preview_inline(mime):
            raise StorageValidationError("UNSUPPORTED_TYPE", "Prévisualisation non autorisée")
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _download_response(svc=svc, doc=doc, obj=obj, inline=True)


@router.post("/{document_id}/links", response_model=DocumentLinkOut, status_code=201)
def create_link(
    document_id: str,
    body: DocumentLinkCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_link(auth, doc)
        link = svc.link_entity(
            document_id=document_id,
            organization_id=org_id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            relation_type=body.relation_type,
            created_by_user_id=auth.user.id if auth.user else None,
        )
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return DocumentLinkOut.model_validate(link)


@router.post("/{document_id}/archive", response_model=DocumentRecordOut)
def archive_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_archive(auth, doc)
        archived = svc.archive(document_id=document_id, organization_id=org_id)
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _serialize_doc(svc, archived)


@router.post("/{document_id}/unarchive", response_model=DocumentRecordOut)
def unarchive_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_archive(auth, doc)
        row = svc.unarchive(document_id=document_id, organization_id=org_id)
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _serialize_doc(svc, row)


@router.post("/{document_id}/delete", response_model=DocumentRecordOut)
def soft_delete_document(
    document_id: str,
    body: DocumentDeleteBody | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_delete(auth, doc)
        row = svc.soft_delete(
            document_id=document_id,
            organization_id=org_id,
            actor_user_id=auth.user.id if auth.user else None,
            reason=(body.reason if body else None),
        )
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _serialize_doc(svc, row)


@router.post("/{document_id}/restore", response_model=DocumentRecordOut)
def restore_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id, allow_deleted=True)
        _policy.assert_can_restore(auth, doc)
        row = svc.restore_soft_deleted(
            document_id=document_id,
            organization_id=org_id,
            actor_user_id=auth.user.id if auth.user else None,
        )
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _serialize_doc(svc, row)


@router.get("/{document_id}/versions", response_model=DocumentVersionListOut)
def list_versions(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_read_versions(auth, doc)
        items = svc.versions.list_versions(document_id, org_id)
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return DocumentVersionListOut(
        items=[_serialize_version(v) for v in items],
        total=len(items),
        current_version_id=doc.current_version_id,
    )


@router.get("/{document_id}/versions/{version_id}", response_model=DocumentVersionOut)
def get_version(
    document_id: str,
    version_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_read_versions(auth, doc)
        ver = svc.versions.get_version(document_id, version_id, org_id)
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _serialize_version(ver)


@router.post("/{document_id}/versions", response_model=DocumentVersionOut, status_code=201)
async def create_version(
    document_id: str,
    file: UploadFile = File(...),
    change_reason: str | None = Form(default=None),
    metadata: str | None = Form(default=None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    meta = _parse_metadata(metadata)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_create_version(auth, doc)
        if not file.filename:
            raise StorageValidationError("INVALID_FILENAME", "Fichier manquant")
        ver = await svc.versions.add_version_from_stream(
            document_id=document_id,
            organization_id=org_id,
            filename=file.filename,
            chunk_iterator=iter_upload_file_chunks(file),
            declared_mime=file.content_type,
            change_reason=change_reason,
            metadata=meta,
            created_by_user_id=auth.user.id if auth.user else None,
        )
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _serialize_version(ver)


@router.get("/{document_id}/versions/{version_id}/download")
def download_version(
    document_id: str,
    version_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    audit = AuditLogger(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        ver = svc.versions.get_version(document_id, version_id, org_id)
        obj = svc.storage.get_object_row(ver.storage_object_id)
        _policy.assert_can_download_version(auth, doc, ver, obj)
        assert obj is not None
        allow_q = obj.status == "quarantined"
        stream = svc.storage.open_stream(obj.id, allow_quarantine=allow_q)
    except DocumentAccessDeniedError as exc:
        audit.record_document_download_denied(
            document_id=document_id,
            organization_id=org_id,
            actor_user_id=auth.user.id if auth.user else None,
            reason=exc.code,
        )
        raise _http_from_storage(exc) from exc
    except StorageError as exc:
        raise _http_from_storage(exc) from exc

    filename = ver.original_filename or obj.safe_filename or "download"
    media = ver.mime_type or obj.mime_type_detected or "application/octet-stream"
    headers = {
        "Content-Disposition": _content_disposition(filename, inline=False),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    }
    if ver.size_bytes:
        headers["Content-Length"] = str(int(ver.size_bytes))

    def _iter():
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            try:
                stream.close()
            except Exception:
                pass

    return StreamingResponse(_iter(), media_type=media, headers=headers)


@router.post("/{document_id}/versions/{version_id}/restore", response_model=DocumentVersionOut)
def restore_version(
    document_id: str,
    version_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Stratégie B : crée une nouvelle version pointant vers l'objet historique."""
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_create_version(auth, doc)
        ver = svc.versions.restore_as_new_version(
            document_id=document_id,
            organization_id=org_id,
            version_id=version_id,
            created_by_user_id=auth.user.id if auth.user else None,
        )
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return _serialize_version(ver)


@router.get("/{document_id}/legal-holds", response_model=LegalHoldListOut)
def list_legal_holds(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    holds_svc = DocumentLegalHoldService(db, audit_logger=AuditLogger(db))
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_read_legal_hold(auth, doc)
        items = holds_svc.list_holds(document_id, org_id)
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return LegalHoldListOut(items=[LegalHoldOut.model_validate(h) for h in items], total=len(items))


@router.post("/{document_id}/legal-holds", response_model=LegalHoldOut, status_code=201)
def place_legal_hold(
    document_id: str,
    body: LegalHoldCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    holds_svc = DocumentLegalHoldService(db, audit_logger=AuditLogger(db))
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_manage_legal_hold(auth, doc)
        hold = holds_svc.place(
            document_id=document_id,
            organization_id=org_id,
            reason=body.reason,
            reference=body.reference,
            placed_by_user_id=auth.user.id if auth.user else None,
            metadata=body.metadata,
        )
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return LegalHoldOut.model_validate(hold)


@router.post("/{document_id}/legal-holds/{hold_id}/release", response_model=LegalHoldOut)
def release_legal_hold(
    document_id: str,
    hold_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = _policy.resolve_organization_id(auth)
    svc = _svc(db)
    holds_svc = DocumentLegalHoldService(db, audit_logger=AuditLogger(db))
    try:
        doc = svc.get_for_organization(document_id, org_id)
        _policy.assert_can_manage_legal_hold(auth, doc)
        hold = holds_svc.release(
            document_id=document_id,
            hold_id=hold_id,
            organization_id=org_id,
            released_by_user_id=auth.user.id if auth.user else None,
        )
    except StorageError as exc:
        raise _http_from_storage(exc) from exc
    return LegalHoldOut.model_validate(hold)

