"""Persistance AI Engine."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.ai.ai_models import ElfisAIExecution, ElfisAIUsage, ElfisDocumentAnalysis


class AIRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_execution(self, execution_id: str) -> ElfisAIExecution | None:
        return (
            self._db.query(ElfisAIExecution)
            .filter(ElfisAIExecution.execution_id == execution_id)
            .first()
        )

    def find_by_idempotency(self, key: str) -> ElfisAIExecution | None:
        if not key:
            return None
        return (
            self._db.query(ElfisAIExecution)
            .filter(ElfisAIExecution.idempotency_key == key)
            .order_by(ElfisAIExecution.created_at.asc())
            .first()
        )

    def save_execution(self, row: ElfisAIExecution, *, commit: bool = True) -> ElfisAIExecution:
        row.updated_at = datetime.utcnow()
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def create_usage(self, row: ElfisAIUsage, *, commit: bool = True) -> ElfisAIUsage:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def list_executions(
        self,
        *,
        organization_id: int | None = None,
        task_name: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisAIExecution], int]:
        q = self._db.query(ElfisAIExecution)
        if organization_id is not None:
            q = q.filter(ElfisAIExecution.organization_id == organization_id)
        if task_name:
            q = q.filter(ElfisAIExecution.task_name == task_name)
        if provider:
            q = q.filter(ElfisAIExecution.provider == provider)
        if model:
            q = q.filter(ElfisAIExecution.model == model)
        if status:
            q = q.filter(ElfisAIExecution.status == status)
        if date_from is not None:
            q = q.filter(ElfisAIExecution.created_at >= date_from)
        if date_to is not None:
            q = q.filter(ElfisAIExecution.created_at <= date_to)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisAIExecution.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def list_usage(
        self,
        *,
        organization_id: int | None = None,
        task_name: str | None = None,
        provider: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisAIUsage], int]:
        q = self._db.query(ElfisAIUsage)
        if organization_id is not None:
            q = q.filter(ElfisAIUsage.organization_id == organization_id)
        if task_name:
            q = q.filter(ElfisAIUsage.task_name == task_name)
        if provider:
            q = q.filter(ElfisAIUsage.provider == provider)
        if date_from is not None:
            q = q.filter(ElfisAIUsage.request_date >= date_from)
        if date_to is not None:
            q = q.filter(ElfisAIUsage.request_date <= date_to)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisAIUsage.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def find_analysis(self, analysis_id: str) -> ElfisDocumentAnalysis | None:
        return (
            self._db.query(ElfisDocumentAnalysis)
            .filter(ElfisDocumentAnalysis.analysis_id == analysis_id)
            .first()
        )

    def find_analysis_for_document(
        self,
        *,
        organization_id: int,
        vault_document_id: str,
        document_version: int,
    ) -> ElfisDocumentAnalysis | None:
        return (
            self._db.query(ElfisDocumentAnalysis)
            .filter(
                ElfisDocumentAnalysis.organization_id == organization_id,
                ElfisDocumentAnalysis.vault_document_id == vault_document_id,
                ElfisDocumentAnalysis.document_version == document_version,
            )
            .first()
        )

    def save_analysis(
        self, row: ElfisDocumentAnalysis, *, commit: bool = True
    ) -> ElfisDocumentAnalysis:
        row.updated_at = datetime.utcnow()
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def list_analyses(
        self,
        *,
        organization_id: int | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisDocumentAnalysis], int]:
        q = self._db.query(ElfisDocumentAnalysis)
        if organization_id is not None:
            q = q.filter(ElfisDocumentAnalysis.organization_id == organization_id)
        if status:
            q = q.filter(ElfisDocumentAnalysis.status == status)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisDocumentAnalysis.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total
