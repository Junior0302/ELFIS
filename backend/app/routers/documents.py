from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.agents.pipeline import process_invoice, refresh_from_manual_edit
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models import Invoice
from app.schemas import InvoiceOut, InvoiceUpdate
from app.services.ocr import ALLOWED_EXT
from app.services.serializers import serialize_invoice
from app.services.storage import resolve_stored, save_upload
from pathlib import Path

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(require_active_subscription)],
)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def _organization_invoice(db: Session, invoice_id: int, organization_id: int) -> Invoice:
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.organization_id == organization_id)
        .first()
    )
    if not invoice:
        raise HTTPException(404, detail="Document introuvable")
    return invoice


@router.post("/upload", response_model=InvoiceOut)
async def upload_document(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    if not file.filename:
        raise HTTPException(400, detail="Fichier manquant")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            400,
            detail="Formats acceptés : PDF, JPG, JPEG, PNG, WEBP (photos & documents)",
        )

    content = await file.read()
    if not content:
        raise HTTPException(400, detail="Fichier vide")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, detail="Fichier trop volumineux (max 15 Mo)")

    stored = await save_upload(file.filename, content)
    invoice = Invoice(
        organization_id=auth.require_organization_id(),
        filename=file.filename,
        stored_path=str(stored),
        mime_type=file.content_type or "application/octet-stream",
        status="processing",
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    try:
        invoice = await process_invoice(db, invoice)
    except Exception as exc:
        invoice.status = "error"
        invoice.needs_review = True
        invoice.anomalies = f'["Échec du pipeline IA: {exc}"]'
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

    return serialize_invoice(invoice)


@router.get("", response_model=list[InvoiceOut])
def list_documents(
    q: str | None = Query(None),
    status: str | None = Query(None),
    needs_review: bool | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    query = (
        db.query(Invoice)
        .filter(Invoice.organization_id == auth.require_organization_id())
        .order_by(Invoice.created_at.desc())
    )
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Invoice.supplier.ilike(like))
            | (Invoice.invoice_number.ilike(like))
            | (Invoice.filename.ilike(like))
        )
    if status:
        query = query.filter(Invoice.status == status)
    if needs_review is not None:
        query = query.filter(Invoice.needs_review.is_(needs_review))
    return [serialize_invoice(i) for i in query.all()]


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_document(
    invoice_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    invoice = _organization_invoice(db, invoice_id, auth.require_organization_id())
    return serialize_invoice(invoice)


@router.patch("/{invoice_id}", response_model=InvoiceOut)
def update_document(
    invoice_id: int,
    payload: InvoiceUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.write")
    invoice = _organization_invoice(db, invoice_id, auth.require_organization_id())

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(invoice, key, value)

    # Régénère validation + écriture comptable après correction humaine
    invoice = refresh_from_manual_edit(db, invoice)
    return serialize_invoice(invoice)


@router.post("/{invoice_id}/reprocess", response_model=InvoiceOut)
async def reprocess_document(
    invoice_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.write")
    invoice = _organization_invoice(db, invoice_id, auth.require_organization_id())
    invoice.status = "processing"
    db.add(invoice)
    db.commit()
    invoice = await process_invoice(db, invoice)
    return serialize_invoice(invoice)


@router.get("/{invoice_id}/file")
def download_original(
    invoice_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    invoice = _organization_invoice(db, invoice_id, auth.require_organization_id())
    path = resolve_stored(invoice.stored_path)
    if not path.exists():
        raise HTTPException(404, detail="Fichier introuvable sur le stockage")
    media = invoice.mime_type or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=invoice.filename)


@router.delete("/{invoice_id}")
def delete_document(
    invoice_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.delete")
    invoice = _organization_invoice(db, invoice_id, auth.require_organization_id())
    path = resolve_stored(invoice.stored_path)
    if path.exists():
        path.unlink(missing_ok=True)
    db.delete(invoice)
    db.commit()
    return {"ok": True}
