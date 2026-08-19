"""Opérations manuelles — jobs, events, users, documents agrégés, recherche."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models_saas import Organization, OrganizationMember, Role, User
from app.platform_admin.admin_audit_service import AdminAuditService
from app.platform_admin.admin_exceptions import AdminActionDeniedError, AdminNotFoundError
from app.platform_admin.admin_security import (
    assert_search_query,
    clamp_page,
    clamp_page_size,
    require_action_reason,
    scrub_dict,
)
from app.platform_admin.admin_types import AdminAuditStatus


class AdminOperationsService:
    def __init__(self, db: Session):
        self.db = db
        self.audit = AdminAuditService(db)

    # --- Users ---
    def list_users(
        self,
        *,
        query: str | None = None,
        organization_id: int | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        page_n = clamp_page(page)
        size = clamp_page_size(page_size)
        q = self.db.query(User)
        if query:
            like = f"%{query.strip()}%"
            q = q.filter(
                or_(User.email.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like))
            )
        if status:
            q = q.filter(User.status == status)
        if organization_id:
            q = q.join(OrganizationMember, OrganizationMember.user_id == User.id).filter(
                OrganizationMember.organization_id == organization_id
            )
        total = q.count()
        users = q.order_by(User.created_at.desc()).offset((page_n - 1) * size).limit(size).all()
        return {
            "users": [self._user_public(u) for u in users],
            "total": total,
            "page": page_n,
            "page_size": size,
        }

    def get_user(self, user_id: int) -> dict[str, Any]:
        user = self.db.get(User, user_id)
        if not user:
            raise AdminNotFoundError("Utilisateur introuvable")
        memberships = (
            self.db.query(OrganizationMember, Organization, Role)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(Role, Role.id == OrganizationMember.role_id)
            .filter(OrganizationMember.user_id == user_id)
            .all()
        )
        return {
            "user": self._user_public(user),
            "memberships": [
                {
                    "organization_id": o.id,
                    "organization_name": o.name,
                    "role": r.name,
                    "status": m.status,
                }
                for m, o, r in memberships
            ],
        }

    def disable_user(self, user_id: int, *, actor: User, reason: str, ip: str | None = None) -> User:
        cleaned = require_action_reason(reason)
        user = self.db.get(User, user_id)
        if not user:
            raise AdminNotFoundError("Utilisateur introuvable")
        if user.is_platform_admin and user.id != actor.id:
            raise AdminActionDeniedError("Impossible de désactiver un autre platform admin")
        prev = {"user_status": user.status}
        user.status = "suspended"
        self.audit.record(
            actor=actor,
            action="user.disable",
            target_type="user",
            target_id=str(user_id),
            reason=cleaned,
            previous_state=prev,
            new_state={"user_status": "suspended"},
            ip=ip,
        )
        self.db.flush()
        return user

    def enable_user(self, user_id: int, *, actor: User, reason: str, ip: str | None = None) -> User:
        cleaned = require_action_reason(reason)
        user = self.db.get(User, user_id)
        if not user:
            raise AdminNotFoundError("Utilisateur introuvable")
        prev = {"user_status": user.status}
        user.status = "active"
        self.audit.record(
            actor=actor,
            action="user.enable",
            target_type="user",
            target_id=str(user_id),
            reason=cleaned,
            previous_state=prev,
            new_state={"user_status": "active"},
            ip=ip,
        )
        self.db.flush()
        return user

    # --- Jobs ---
    def retry_job(self, job_id: str, *, actor: User, reason: str, ip: str | None = None) -> dict:
        cleaned = require_action_reason(reason)
        from app.jobs.job_service import JobService

        job = JobService(self.db).retry_job(job_id, actor_user_id=actor.id)
        self.audit.record(
            actor=actor,
            action="job.manual_retry",
            target_type="job",
            target_id=job_id,
            organization_id=job.organization_id,
            reason=cleaned,
            new_state={"job_status": job.status},
            ip=ip,
        )
        return {"job_id": job.job_id, "status": job.status}

    def cancel_job(self, job_id: str, *, actor: User, reason: str, ip: str | None = None) -> dict:
        cleaned = require_action_reason(reason)
        from app.jobs.job_service import JobService

        job = JobService(self.db).cancel_job(job_id, actor_user_id=actor.id)
        self.audit.record(
            actor=actor,
            action="job.manual_cancel",
            target_type="job",
            target_id=job_id,
            organization_id=job.organization_id,
            reason=cleaned,
            new_state={"job_status": job.status},
            ip=ip,
        )
        return {"job_id": job.job_id, "status": job.status}

    # --- Events ---
    def retry_event(self, event_id: str, *, actor: User, reason: str, ip: str | None = None) -> dict:
        cleaned = require_action_reason(reason)
        from app.events.event_models import ElfisEvent
        from app.events.event_repository import EventRepository

        row = EventRepository(self.db).find_by_event_id(event_id)
        if not row:
            raise AdminNotFoundError("Événement introuvable")
        if row.status not in {"failed", "dead_letter", "retry"}:
            raise AdminActionDeniedError(f"Retry non autorisé pour le statut {row.status}")
        prev = {"event_status": row.status}
        now = datetime.utcnow()
        row.status = "pending"
        row.available_at = now
        row.locked_at = None
        row.locked_by = None
        row.failed_at = None
        row.last_error = None
        row.updated_at = now
        self.db.flush()
        self.audit.record(
            actor=actor,
            action="event.manual_retry",
            target_type="event",
            target_id=event_id,
            organization_id=row.organization_id,
            reason=cleaned,
            previous_state=prev,
            new_state={"event_status": "pending"},
            ip=ip,
        )
        return {"event_id": row.event_id, "status": row.status}

    def mark_event_resolved(
        self, event_id: str, *, actor: User, reason: str, ip: str | None = None
    ) -> dict:
        cleaned = require_action_reason(reason)
        from app.events.event_repository import EventRepository

        row = EventRepository(self.db).find_by_event_id(event_id)
        if not row:
            raise AdminNotFoundError("Événement introuvable")
        prev = {"event_status": row.status}
        row.status = "processed"
        row.processed_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self.db.flush()
        self.audit.record(
            actor=actor,
            action="event.mark_resolved",
            target_type="event",
            target_id=event_id,
            organization_id=row.organization_id,
            reason=cleaned,
            previous_state=prev,
            new_state={"event_status": "processed"},
            ip=ip,
        )
        return {"event_id": row.event_id, "status": row.status}

    # --- Documents aggregate ---
    def get_document_aggregate(self, vault_document_id: str) -> dict[str, Any]:
        from app.models_vault import VaultDocument

        doc = (
            self.db.query(VaultDocument)
            .filter(VaultDocument.id == vault_document_id)
            .first()
        )
        if not doc:
            raise AdminNotFoundError("Document introuvable")
        extraction = None
        analysis = None
        proposal = None
        try:
            from app.document_intelligence.document_models import ElfisDocumentTextExtraction

            extraction = (
                self.db.query(ElfisDocumentTextExtraction)
                .filter(ElfisDocumentTextExtraction.vault_document_id == vault_document_id)
                .order_by(ElfisDocumentTextExtraction.created_at.desc())
                .first()
            )
        except Exception:
            pass
        try:
            from app.ai.ai_models import ElfisDocumentAnalysis

            analysis = (
                self.db.query(ElfisDocumentAnalysis)
                .filter(ElfisDocumentAnalysis.vault_document_id == vault_document_id)
                .order_by(ElfisDocumentAnalysis.created_at.desc())
                .first()
            )
        except Exception:
            pass
        try:
            from app.accounting.accounting_models import ElfisAccountingProposal

            proposal = (
                self.db.query(ElfisAccountingProposal)
                .filter(ElfisAccountingProposal.vault_document_id == vault_document_id)
                .order_by(ElfisAccountingProposal.created_at.desc())
                .first()
            )
        except Exception:
            pass
        return scrub_dict(
            {
                "document": {
                    "vault_document_id": doc.id,
                    "organization_id": doc.organization_id,
                    "document_type": doc.document_type,
                    "document_number": doc.document_number,
                    "original_filename": doc.original_filename,
                    "mime_type": doc.mime_type,
                    "file_size": doc.file_size,
                    "amount_ttc": float(doc.amount_ttc) if doc.amount_ttc is not None else None,
                    "currency": doc.currency,
                    "created_at": doc.created_at,
                    "has_pdf": True,
                    "pdf_included": False,
                },
                "extraction": {
                    "extraction_id": getattr(extraction, "extraction_id", None),
                    "status": getattr(extraction, "status", None),
                    "text_preview": None,
                }
                if extraction
                else None,
                "analysis": {
                    "analysis_id": getattr(analysis, "analysis_id", None),
                    "status": getattr(analysis, "status", None),
                    "document_type": getattr(analysis, "document_type", None),
                }
                if analysis
                else None,
                "accounting_proposal": {
                    "proposal_id": getattr(proposal, "proposal_id", None),
                    "status": getattr(proposal, "status", None),
                }
                if proposal
                else None,
            }
        )

    def list_documents(
        self,
        *,
        organization_id: int | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        from app.models_vault import VaultDocument

        page_n = clamp_page(page)
        size = clamp_page_size(page_size)
        q = self.db.query(VaultDocument)
        if organization_id:
            q = q.filter(VaultDocument.organization_id == organization_id)
        total = q.count()
        rows = q.order_by(VaultDocument.created_at.desc()).offset((page_n - 1) * size).limit(size).all()
        return {
            "documents": [
                {
                    "vault_document_id": d.id,
                    "organization_id": d.organization_id,
                    "document_type": d.document_type,
                    "document_number": d.document_number,
                    "original_filename": d.original_filename,
                    "file_size": d.file_size,
                    "created_at": d.created_at,
                }
                for d in rows
            ],
            "total": total,
            "page": page_n,
            "page_size": size,
        }

    # --- Global search ---
    def global_search(self, q: str) -> dict[str, Any]:
        from app.config import settings

        query = assert_search_query(q)
        limit = int(getattr(settings, "elfis_platform_admin_search_limit", 20) or 20)
        like = f"%{query}%"
        orgs = (
            self.db.query(Organization)
            .filter(or_(Organization.name.ilike(like), Organization.email.ilike(like)))
            .limit(limit)
            .all()
        )
        users = (
            self.db.query(User)
            .filter(or_(User.email.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like)))
            .limit(limit)
            .all()
        )
        results: dict[str, list] = {
            "organizations": [{"id": o.id, "name": o.name, "email": o.email} for o in orgs],
            "users": [{"id": u.id, "email": u.email} for u in users],
            "documents": [],
            "jobs": [],
            "incidents": [],
        }
        try:
            from app.models_vault import VaultDocument

            docs = (
                self.db.query(VaultDocument)
                .filter(
                    or_(
                        VaultDocument.document_number.ilike(like),
                        VaultDocument.original_filename.ilike(like),
                        VaultDocument.id.ilike(like),
                    )
                )
                .limit(limit)
                .all()
            )
            results["documents"] = [
                {"id": d.id, "organization_id": d.organization_id, "filename": d.original_filename}
                for d in docs
            ]
        except Exception:
            pass
        try:
            from app.jobs.job_models import ElfisJob

            jobs = (
                self.db.query(ElfisJob)
                .filter(or_(ElfisJob.job_id.ilike(like), ElfisJob.job_name.ilike(like)))
                .limit(limit)
                .all()
            )
            results["jobs"] = [
                {"id": j.job_id, "job_name": j.job_name, "status": j.status, "organization_id": j.organization_id}
                for j in jobs
            ]
        except Exception:
            pass
        try:
            from app.platform_admin.admin_models import ElfisOperationalIncident

            incidents = (
                self.db.query(ElfisOperationalIncident)
                .filter(
                    or_(
                        ElfisOperationalIncident.incident_id.ilike(like),
                        ElfisOperationalIncident.title.ilike(like),
                    )
                )
                .limit(limit)
                .all()
            )
            results["incidents"] = [
                {"id": i.incident_id, "title": i.title, "status": i.status, "type": i.incident_type}
                for i in incidents
            ]
        except Exception:
            pass
        return {"query": query, "results": results}

    def _user_public(self, user: User) -> dict[str, Any]:
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "status": user.status,
            "is_platform_admin": bool(user.is_platform_admin),
            "last_login": user.last_login,
            "created_at": user.created_at,
        }
