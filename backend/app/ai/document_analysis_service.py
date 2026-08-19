"""Orchestration analyse document Vault → extraction texte → jobs AI."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.ai.ai_exceptions import AINotFoundError
from app.ai.ai_models import ElfisDocumentAnalysis
from app.ai.ai_repository import AIRepository
from app.ai.ai_schemas import DocumentAnalyzeAccepted, DocumentAnalysisView
from app.ai.ai_types import DocumentAnalysisStatus
from app.config import settings
from app.document_intelligence.document_repository import DocumentExtractionRepository
from app.document_intelligence.document_types import ExtractionStatus
from app.jobs import bootstrap_job_handlers
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames
from app.models_vault import VaultDocument


class DocumentAnalysisService:
    def __init__(self, db: Session):
        self._db = db
        self._repo = AIRepository(db)

    def start_analysis(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        vault_document_id: str,
        extracted_text: str | None = None,
        filename: str | None = None,
    ) -> DocumentAnalyzeAccepted:
        bootstrap_job_handlers()
        doc = (
            self._db.query(VaultDocument)
            .filter(VaultDocument.id == vault_document_id)
            .first()
        )
        if not doc or doc.organization_id != organization_id:
            raise AINotFoundError("Document introuvable")

        version = int(doc.version or 1)
        existing = self._repo.find_analysis_for_document(
            organization_id=organization_id,
            vault_document_id=vault_document_id,
            document_version=version,
        )
        if existing and existing.status not in (
            DocumentAnalysisStatus.FAILED,
            DocumentAnalysisStatus.BLOCKED,
            DocumentAnalysisStatus.PENDING,
        ):
            return DocumentAnalyzeAccepted(
                analysis_id=existing.analysis_id,
                vault_document_id=vault_document_id,
                status=existing.status,
                current_stage=existing.current_stage,
                job_id=None,
                reused_existing_analysis=True,
            )

        now = datetime.utcnow()
        text = (extracted_text or "").strip()
        analysis = existing or ElfisDocumentAnalysis(
            id=str(uuid.uuid4()),
            analysis_id=str(uuid.uuid4()),
            organization_id=organization_id,
            vault_document_id=vault_document_id,
            document_version=version,
            status=DocumentAnalysisStatus.PENDING,
            requires_review=False,
            current_stage="classification",
            ai_execution_ids=[],
            created_at=now,
            updated_at=now,
        )

        # Texte fourni explicitement → classification directe (compat)
        if text:
            return self._enqueue_classification(
                analysis=analysis,
                organization_id=organization_id,
                user_id=user_id,
                vault_document_id=vault_document_id,
                version=version,
                filename=filename or doc.original_filename,
                mime_type=doc.mime_type,
                text=text,
                extraction_id=None,
            )

        # Sinon : chercher une extraction Document Intelligence completed
        di_repo = DocumentExtractionRepository(self._db)
        extraction = di_repo.find_for_document(
            organization_id=organization_id,
            vault_document_id=vault_document_id,
            document_version=version,
        )

        if extraction and extraction.status == ExtractionStatus.REQUIRES_OCR:
            ocr_ready = settings.elfis_ocr_enabled and (
                (settings.elfis_ocr_provider or "").lower() != "disabled"
            )
            if not ocr_ready:
                analysis.status = DocumentAnalysisStatus.BLOCKED
                analysis.current_stage = "awaiting_ocr"
                analysis.requires_review = True
                analysis.updated_at = now
                self._repo.save_analysis(analysis)
                return DocumentAnalyzeAccepted(
                    analysis_id=analysis.analysis_id,
                    vault_document_id=vault_document_id,
                    status=analysis.status,
                    current_stage=analysis.current_stage,
                    job_id=None,
                    reused_existing_analysis=False,
                )

        if (
            extraction
            and extraction.status == ExtractionStatus.COMPLETED
            and (extraction.text_content or "").strip()
            and not extraction.requires_ocr
        ):
            return self._enqueue_classification(
                analysis=analysis,
                organization_id=organization_id,
                user_id=user_id,
                vault_document_id=vault_document_id,
                version=version,
                filename=filename or doc.original_filename or extraction.filename,
                mime_type=doc.mime_type or extraction.mime_type,
                text=None,
                extraction_id=extraction.extraction_id,
            )

        # Pas de texte → enqueue extract_text, stage text_extraction
        analysis.status = DocumentAnalysisStatus.PENDING
        analysis.current_stage = "text_extraction"
        analysis.updated_at = now
        self._repo.save_analysis(analysis)

        idem = f"document-text:{organization_id}:{vault_document_id}:{version}"
        job = JobService(self._db).enqueue(
            JobRequest(
                job_name=JobNames.VAULT_DOCUMENT_EXTRACT_TEXT,
                organization_id=organization_id,
                user_id=user_id,
                queue_name="default",
                payload={
                    "vault_document_id": vault_document_id,
                    "document_version": version,
                    "idempotency_key": idem,
                },
                idempotency_key=idem,
                correlation_id=str(uuid.uuid4()),
            )
        )
        return DocumentAnalyzeAccepted(
            analysis_id=analysis.analysis_id,
            vault_document_id=vault_document_id,
            status=analysis.status,
            current_stage=analysis.current_stage,
            job_id=job.job_id,
            reused_existing_analysis=False,
        )

    def _enqueue_classification(
        self,
        *,
        analysis: ElfisDocumentAnalysis,
        organization_id: int,
        user_id: int | None,
        vault_document_id: str,
        version: int,
        filename: str | None,
        mime_type: str | None,
        text: str | None,
        extraction_id: str | None,
    ) -> DocumentAnalyzeAccepted:
        now = datetime.utcnow()
        analysis.status = DocumentAnalysisStatus.CLASSIFYING
        analysis.current_stage = "classification"
        analysis.updated_at = now
        self._repo.save_analysis(analysis)

        payload: dict = {
            "vault_document_id": vault_document_id,
            "analysis_id": analysis.analysis_id,
            "filename": filename,
            "mime_type": mime_type,
            "document_version": version,
        }
        if extraction_id:
            payload["extraction_id"] = extraction_id
        elif text:
            payload["extracted_text"] = text[:40_000]

        job = JobService(self._db).enqueue(
            JobRequest(
                job_name=JobNames.VAULT_DOCUMENT_AI_CLASSIFICATION,
                organization_id=organization_id,
                user_id=user_id,
                queue_name="default",
                payload=payload,
                idempotency_key=f"ai-classify:{organization_id}:{vault_document_id}:{version}",
                correlation_id=str(uuid.uuid4()),
            )
        )
        return DocumentAnalyzeAccepted(
            analysis_id=analysis.analysis_id,
            vault_document_id=vault_document_id,
            status=analysis.status,
            current_stage=analysis.current_stage,
            job_id=job.job_id,
            reused_existing_analysis=False,
        )

    def get_analysis_for_document(
        self, *, organization_id: int, vault_document_id: str
    ) -> DocumentAnalysisView:
        doc = (
            self._db.query(VaultDocument)
            .filter(VaultDocument.id == vault_document_id)
            .first()
        )
        if not doc or doc.organization_id != organization_id:
            raise AINotFoundError("Document introuvable")
        row = self._repo.find_analysis_for_document(
            organization_id=organization_id,
            vault_document_id=vault_document_id,
            document_version=int(doc.version or 1),
        )
        if not row:
            raise AINotFoundError("Analyse introuvable")
        quality = row.quality if isinstance(row.quality, dict) else None
        quality_summary = None
        if quality:
            quality_summary = {
                "status": quality.get("status"),
                "confidence": quality.get("confidence"),
                "requires_review": quality.get("requires_review"),
                "errors_count": len(quality.get("errors") or []),
                "warnings_count": len(quality.get("warnings") or []),
            }
        return DocumentAnalysisView(
            analysis_id=row.analysis_id,
            status=row.status,
            current_stage=row.current_stage,
            document_type=row.document_type,
            confidence=float(row.confidence) if row.confidence is not None else None,
            requires_review=bool(row.requires_review),
            quality_summary=quality_summary,
            created_at=row.created_at,
            updated_at=row.updated_at,
            completed_at=row.completed_at,
        )
