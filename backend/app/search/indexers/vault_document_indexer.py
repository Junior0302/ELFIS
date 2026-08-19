"""Indexer VaultDocument."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.document_intelligence.document_models import ElfisDocumentTextExtraction
from app.document_intelligence.document_types import ExtractionStatus
from app.models_vault import VaultDocument
from app.search.indexers.base import ResourceIndexer
from app.search.search_exceptions import SearchNotFoundError
from app.search.search_schemas import BuiltSearchDocument
from app.search.search_security import (
    assert_action_url,
    content_hash,
    filter_metadata,
    sanitize_indexed_text,
    truncate_content,
)
from app.search.search_types import SearchCategories, SearchResourceTypes


class VaultDocumentIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.VAULT_DOCUMENT

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> VaultDocument:
        doc = db.query(VaultDocument).filter(VaultDocument.id == resource_id).first()
        if not doc or doc.organization_id != organization_id:
            raise SearchNotFoundError("Document Vault introuvable")
        return doc

    def build_search_document(
        self,
        resource: VaultDocument,
        *,
        organization_id: int,
        resource_version: int = 1,
        db: Session | None = None,
    ) -> BuiltSearchDocument:
        title = resource.original_filename or resource.document_number or f"Document {resource.id}"
        subtitle_parts = [resource.document_type or "", resource.document_number or ""]
        subtitle = " · ".join(p for p in subtitle_parts if p) or None

        excerpt = ""
        if db is not None:
            extraction = (
                db.query(ElfisDocumentTextExtraction)
                .filter(
                    ElfisDocumentTextExtraction.organization_id == organization_id,
                    ElfisDocumentTextExtraction.vault_document_id == resource.id,
                    ElfisDocumentTextExtraction.document_version
                    == int(resource.version or resource_version or 1),
                    ElfisDocumentTextExtraction.status == ExtractionStatus.COMPLETED,
                )
                .first()
            )
            if extraction and extraction.text_content:
                excerpt = truncate_content(extraction.text_content)[:4000]

        search_parts = [
            title,
            subtitle or "",
            resource.document_type or "",
            resource.document_number or "",
            resource.archive_status or "",
            resource.currency or "",
            excerpt,
        ]
        search_text = sanitize_indexed_text("\n".join(search_parts))
        content = truncate_content(excerpt) if excerpt else None
        ch = content_hash(title, subtitle or "", search_text, str(resource.amount_ttc or ""))

        doc_date = None
        if resource.invoice_date:
            doc_date = datetime.combine(resource.invoice_date, datetime.min.time())
        elif resource.archived_at:
            doc_date = resource.archived_at
        elif resource.created_at:
            doc_date = resource.created_at

        amount = float(resource.amount_ttc) if resource.amount_ttc is not None else None
        meta = filter_metadata(
            {
                "document_type": resource.document_type,
                "mime_type": resource.mime_type,
                "archive_status": resource.archive_status,
                "version": resource.version,
                "language": None,
            }
        )
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(resource.id),
            resource_version=int(resource.version or resource_version or 1),
            title=title[:512],
            subtitle=(subtitle or "")[:512] or None,
            content=content,
            search_text=search_text,
            status=resource.archive_status,
            category=SearchCategories.DOCUMENT,
            document_date=doc_date,
            amount=amount,
            currency=resource.currency,
            action_url=assert_action_url(f"/documents/{resource.id}"),
            metadata=meta,
            content_hash=ch,
        )
