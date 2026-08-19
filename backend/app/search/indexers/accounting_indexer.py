"""Indexer propositions et écritures comptables."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.accounting.accounting_models import ElfisAccountingEntry, ElfisAccountingProposal
from app.search.indexers.base import ResourceIndexer
from app.search.search_exceptions import SearchNotFoundError
from app.search.search_schemas import BuiltSearchDocument
from app.search.search_security import (
    assert_action_url,
    content_hash,
    filter_metadata,
    sanitize_indexed_text,
)
from app.search.search_types import SearchCategories, SearchResourceTypes


class AccountingProposalIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.ACCOUNTING_PROPOSAL

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(
        self, db: Session, *, organization_id: int, resource_id: str
    ) -> ElfisAccountingProposal:
        row = (
            db.query(ElfisAccountingProposal)
            .filter(ElfisAccountingProposal.proposal_id == resource_id)
            .first()
        )
        if not row or row.organization_id != organization_id:
            raise SearchNotFoundError("Proposition comptable introuvable")
        return row

    def build_search_document(
        self,
        resource: ElfisAccountingProposal,
        *,
        organization_id: int,
        resource_version: int = 1,
        db: Session | None = None,
    ) -> BuiltSearchDocument:
        title = resource.document_number or f"Proposition {resource.proposal_id[:8]}"
        party = resource.supplier_name or resource.customer_name
        subtitle = " · ".join(p for p in [resource.document_type or "", str(party or "")] if p)

        mapping = resource.accounting_mapping if isinstance(resource.accounting_mapping, dict) else {}
        journal = mapping.get("journal_code") or ""
        accounts = []
        for line in (mapping.get("lines") or [])[:6]:
            if isinstance(line, dict) and line.get("account_code"):
                accounts.append(str(line["account_code"]))
        reasons = list(resource.review_reasons or [])[:5]

        search_parts = [
            title,
            subtitle,
            resource.status or "",
            journal,
            " ".join(accounts),
            " ".join(str(r) for r in reasons),
            str(resource.amount_ttc or ""),
        ]
        search_text = sanitize_indexed_text("\n".join(search_parts))
        amount = float(resource.amount_ttc) if resource.amount_ttc is not None else None
        doc_date = None
        if resource.document_date:
            doc_date = datetime.combine(resource.document_date, datetime.min.time())
        elif resource.created_at:
            doc_date = resource.created_at

        meta = filter_metadata(
            {
                "requires_review": bool(resource.requires_review),
                "confidence": float(resource.confidence) if resource.confidence is not None else None,
                "journal_code": journal or None,
                "main_accounts": accounts,
                "review_reasons": reasons,
                "vault_document_id": resource.vault_document_id,
            }
        )
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(resource.proposal_id),
            resource_version=int(resource.document_version or resource_version or 1),
            title=str(title)[:512],
            subtitle=subtitle[:512] if subtitle else None,
            content=None,
            search_text=search_text,
            status=resource.status,
            category=SearchCategories.ACCOUNTING,
            document_date=doc_date,
            amount=amount,
            currency=resource.currency or "EUR",
            action_url=assert_action_url(f"/accounting/proposals/{resource.proposal_id}"),
            metadata=meta,
            content_hash=content_hash(str(title), search_text, resource.status or ""),
        )


class AccountingEntryIndexer(ResourceIndexer):
    resource_type = SearchResourceTypes.ACCOUNTING_ENTRY

    def supports(self, resource_type: str) -> bool:
        return resource_type == self.resource_type

    def load_resource(
        self, db: Session, *, organization_id: int, resource_id: str
    ) -> ElfisAccountingEntry:
        row = (
            db.query(ElfisAccountingEntry)
            .filter(ElfisAccountingEntry.entry_id == resource_id)
            .first()
        )
        if not row or row.organization_id != organization_id:
            raise SearchNotFoundError("Écriture comptable introuvable")
        return row

    def build_search_document(
        self,
        resource: ElfisAccountingEntry,
        *,
        organization_id: int,
        resource_version: int = 1,
    ) -> BuiltSearchDocument:
        title = resource.reference or resource.description or f"Écriture {resource.entry_id[:8]}"
        search_text = sanitize_indexed_text(
            "\n".join(
                [
                    str(title),
                    resource.journal_code or "",
                    resource.description or "",
                    resource.status or "",
                    str(resource.total_debit or ""),
                    str(resource.total_credit or ""),
                ]
            )
        )
        doc_date = None
        if resource.entry_date:
            doc_date = datetime.combine(resource.entry_date, datetime.min.time())
        amount = float(resource.total_debit) if resource.total_debit is not None else None
        return BuiltSearchDocument(
            organization_id=organization_id,
            resource_type=self.resource_type,
            resource_id=str(resource.entry_id),
            resource_version=resource_version,
            title=str(title)[:512],
            subtitle=resource.journal_code,
            content=None,
            search_text=search_text,
            status=resource.status,
            category=SearchCategories.ACCOUNTING,
            document_date=doc_date,
            amount=amount,
            currency=resource.currency or "EUR",
            action_url=assert_action_url(f"/accounting/proposals/{resource.proposal_id}"),
            metadata=filter_metadata(
                {
                    "proposal_id": resource.proposal_id,
                    "balanced": bool(resource.balanced),
                    "journal_code": resource.journal_code,
                }
            ),
            content_hash=content_hash(str(title), search_text, resource.status or ""),
        )
