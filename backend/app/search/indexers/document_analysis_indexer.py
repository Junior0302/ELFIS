"""Indexer analysis + extraction texte."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.ai.ai_models import ElfisDocumentAnalysis
from app.document_intelligence.document_models import ElfisDocumentTextExtraction
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


def _extraction_fields(extraction: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(extraction, dict):
        return {}
    inv = extraction.get("invoice") if isinstance(extraction.get("invoice"), dict) else {}
    amounts = extraction.get("amounts") if isinstance(extraction.get("amounts"), dict) else {}
    supplier = extraction.get("supplier") if isinstance(extraction.get("supplier"), dict) else {}
    customer = extraction.get("customer") if isinstance(extraction.get("customer"), dict) else {}
    return {
        "document_number": inv.get("number") or extraction.get("document_number"),
        "supplier_name": supplier.get("name") or extraction.get("supplier_name"),
        "customer_name": customer.get("name") or extraction.get("customer_name"),
        "amount_ht": amounts.get("ht") or extraction.get("amount_ht"),
        "amount_vat": amounts.get("vat") or extraction.get("amount_vat"),
        "amount_ttc": amounts.get("ttc") or extraction.get("amount_ttc"),
        "currency": amounts.get("currency") or extraction.get("currency"),
    }


class DocumentAnalysisIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.DOCUMENT_ANALYSIS

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(
        self, db: Session, *, organization_id: int, resource_id: str
    ) -> ElfisDocumentAnalysis:
        row = (
            db.query(ElfisDocumentAnalysis)
            .filter(ElfisDocumentAnalysis.analysis_id == resource_id)
            .first()
        )
        if not row or row.organization_id != organization_id:
            raise SearchNotFoundError("Analyse introuvable")
        return row

    def build_search_document(
        self,
        resource: ElfisDocumentAnalysis,
        *,
        organization_id: int,
        resource_version: int = 1,
        db: Session | None = None,
    ) -> BuiltSearchDocument:
        fields = _extraction_fields(resource.extraction if isinstance(resource.extraction, dict) else {})
        title = (
            fields.get("document_number")
            or resource.document_type
            or f"Analyse {resource.analysis_id[:8]}"
        )
        party = fields.get("supplier_name") or fields.get("customer_name")
        subtitle = " · ".join(
            p for p in [resource.document_type or "", str(party or "")] if p
        ) or None

        # Texte extrait limité — une seule copie courte
        text_excerpt = ""
        if db is not None:
            tex = (
                db.query(ElfisDocumentTextExtraction)
                .filter(
                    ElfisDocumentTextExtraction.organization_id == organization_id,
                    ElfisDocumentTextExtraction.vault_document_id == resource.vault_document_id,
                    ElfisDocumentTextExtraction.document_version
                    == int(resource.document_version or resource_version or 1),
                )
                .first()
            )
            if tex and tex.text_content:
                text_excerpt = truncate_content(tex.text_content)[:8000]

        search_parts = [
            str(title),
            subtitle or "",
            resource.document_type or "",
            resource.status or "",
            str(fields.get("document_number") or ""),
            str(fields.get("supplier_name") or ""),
            str(fields.get("customer_name") or ""),
            text_excerpt[:2000],
        ]
        search_text = sanitize_indexed_text("\n".join(search_parts))
        amount = fields.get("amount_ttc")
        try:
            amount_f = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            amount_f = None

        meta = filter_metadata(
            {
                "document_type": resource.document_type,
                "confidence": float(resource.confidence) if resource.confidence is not None else None,
                "requires_review": bool(resource.requires_review),
                "vault_document_id": resource.vault_document_id,
                "quality_status": (resource.quality or {}).get("status")
                if isinstance(resource.quality, dict)
                else None,
            }
        )
        ch = content_hash(str(title), search_text, resource.status or "", str(amount_f or ""))
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(resource.analysis_id),
            resource_version=int(resource.document_version or resource_version or 1),
            title=str(title)[:512],
            subtitle=(subtitle or "")[:512] or None,
            content=truncate_content(text_excerpt) if text_excerpt else None,
            search_text=search_text,
            status=resource.status,
            category=SearchCategories.ANALYSIS,
            document_date=resource.updated_at or resource.created_at,
            amount=amount_f,
            currency=str(fields.get("currency") or "EUR") if fields.get("currency") else "EUR",
            action_url=assert_action_url(f"/documents/{resource.vault_document_id}"),
            metadata=meta,
            content_hash=ch,
        )


class DocumentTextExtractionIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.DOCUMENT_TEXT_EXTRACTION

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(
        self, db: Session, *, organization_id: int, resource_id: str
    ) -> ElfisDocumentTextExtraction:
        row = (
            db.query(ElfisDocumentTextExtraction)
            .filter(ElfisDocumentTextExtraction.extraction_id == resource_id)
            .first()
        )
        if not row or row.organization_id != organization_id:
            raise SearchNotFoundError("Extraction introuvable")
        return row

    def build_search_document(
        self,
        resource: ElfisDocumentTextExtraction,
        *,
        organization_id: int,
        resource_version: int = 1,
    ) -> BuiltSearchDocument:
        title = resource.filename or f"Extraction {resource.extraction_id[:8]}"
        content = truncate_content(resource.text_content)
        search_text = sanitize_indexed_text(
            "\n".join(
                [
                    title,
                    resource.status or "",
                    resource.extractor_name or "",
                    (content or "")[:4000],
                ]
            )
        )
        meta = filter_metadata(
            {
                "extractor_name": resource.extractor_name,
                "requires_ocr": bool(resource.requires_ocr),
                "requires_review": bool(resource.requires_review),
                "vault_document_id": resource.vault_document_id,
                "text_length": resource.text_length,
            }
        )
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(resource.extraction_id),
            resource_version=int(resource.document_version or resource_version or 1),
            title=title[:512],
            subtitle=resource.extractor_name,
            content=content,
            search_text=search_text,
            status=resource.status,
            category=SearchCategories.ANALYSIS,
            document_date=resource.completed_at or resource.created_at,
            amount=None,
            currency=None,
            action_url=assert_action_url(f"/documents/{resource.vault_document_id}"),
            metadata=meta,
            content_hash=content_hash(title, search_text, resource.status or ""),
        )
