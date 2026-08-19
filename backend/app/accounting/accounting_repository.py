"""Persistance Accounting Pipeline."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.accounting.accounting_models import (
    ElfisAccountingEntry,
    ElfisAccountingEntryLine,
    ElfisAccountingProposal,
    ElfisAccountingReview,
)


class AccountingRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_proposal(self, proposal_id: str) -> ElfisAccountingProposal | None:
        return (
            self._db.query(ElfisAccountingProposal)
            .filter(ElfisAccountingProposal.proposal_id == proposal_id)
            .first()
        )

    def find_proposal_for_document(
        self,
        *,
        organization_id: int,
        vault_document_id: str,
        document_version: int,
    ) -> ElfisAccountingProposal | None:
        return (
            self._db.query(ElfisAccountingProposal)
            .filter(
                ElfisAccountingProposal.organization_id == organization_id,
                ElfisAccountingProposal.vault_document_id == vault_document_id,
                ElfisAccountingProposal.document_version == document_version,
            )
            .first()
        )

    def find_by_idempotency(self, key: str) -> ElfisAccountingProposal | None:
        if not key:
            return None
        return (
            self._db.query(ElfisAccountingProposal)
            .filter(ElfisAccountingProposal.idempotency_key == key)
            .order_by(ElfisAccountingProposal.created_at.asc())
            .first()
        )

    def save_proposal(
        self, row: ElfisAccountingProposal, *, commit: bool = True
    ) -> ElfisAccountingProposal:
        row.updated_at = datetime.utcnow()
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def find_active_entry(self, proposal_id: str) -> ElfisAccountingEntry | None:
        return (
            self._db.query(ElfisAccountingEntry)
            .filter(
                ElfisAccountingEntry.proposal_id == proposal_id,
                ElfisAccountingEntry.status.in_(["draft", "proposed", "validated"]),
            )
            .order_by(ElfisAccountingEntry.created_at.desc())
            .first()
        )

    def find_entry(self, entry_id: str) -> ElfisAccountingEntry | None:
        return (
            self._db.query(ElfisAccountingEntry)
            .filter(ElfisAccountingEntry.entry_id == entry_id)
            .first()
        )

    def list_lines(self, entry_id: str) -> list[ElfisAccountingEntryLine]:
        return (
            self._db.query(ElfisAccountingEntryLine)
            .filter(ElfisAccountingEntryLine.entry_id == entry_id)
            .order_by(ElfisAccountingEntryLine.line_number.asc())
            .all()
        )

    def delete_lines(self, entry_id: str) -> None:
        self._db.query(ElfisAccountingEntryLine).filter(
            ElfisAccountingEntryLine.entry_id == entry_id
        ).delete()

    def save_entry(self, row: ElfisAccountingEntry, *, commit: bool = True) -> ElfisAccountingEntry:
        row.updated_at = datetime.utcnow()
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def save_line(
        self, row: ElfisAccountingEntryLine, *, commit: bool = False
    ) -> ElfisAccountingEntryLine:
        row.updated_at = datetime.utcnow()
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def add_review(
        self, row: ElfisAccountingReview, *, commit: bool = True
    ) -> ElfisAccountingReview:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def list_reviews(
        self, proposal_id: str, *, limit: int = 50
    ) -> list[ElfisAccountingReview]:
        return (
            self._db.query(ElfisAccountingReview)
            .filter(ElfisAccountingReview.proposal_id == proposal_id)
            .order_by(ElfisAccountingReview.created_at.desc())
            .limit(max(1, min(100, limit)))
            .all()
        )

    def list_proposals(
        self,
        *,
        organization_id: int | None = None,
        status: str | None = None,
        document_type: str | None = None,
        requires_review: bool | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisAccountingProposal], int]:
        q = self._db.query(ElfisAccountingProposal)
        if organization_id is not None:
            q = q.filter(ElfisAccountingProposal.organization_id == organization_id)
        if status:
            q = q.filter(ElfisAccountingProposal.status == status)
        if document_type:
            q = q.filter(ElfisAccountingProposal.document_type == document_type)
        if requires_review is not None:
            q = q.filter(ElfisAccountingProposal.requires_review == requires_review)
        if date_from is not None:
            q = q.filter(ElfisAccountingProposal.created_at >= date_from)
        if date_to is not None:
            q = q.filter(ElfisAccountingProposal.created_at <= date_to)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisAccountingProposal.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def list_entries(
        self,
        *,
        organization_id: int | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisAccountingEntry], int]:
        q = self._db.query(ElfisAccountingEntry)
        if organization_id is not None:
            q = q.filter(ElfisAccountingEntry.organization_id == organization_id)
        if status:
            q = q.filter(ElfisAccountingEntry.status == status)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisAccountingEntry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def list_all_reviews(
        self,
        *,
        organization_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisAccountingReview], int]:
        q = self._db.query(ElfisAccountingReview)
        if organization_id is not None:
            q = q.filter(ElfisAccountingReview.organization_id == organization_id)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisAccountingReview.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total
