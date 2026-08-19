"""Helpers d'audit métier — délèguent à AuditService."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.audit.audit_context import AuditContext
from app.audit.audit_service import AuditService
from app.audit.audit_types import AuditAction, AuditCategory, AuditStatus, Severity


class AuditLogger:
    def __init__(
        self,
        db: Session | None = None,
        *,
        service: AuditService | None = None,
        isolated_writes: bool = True,
    ) -> None:
        self._service = service or AuditService(db, isolated_writes=isolated_writes)

    @property
    def service(self) -> AuditService:
        return self._service

    def record_login_success(
        self,
        *,
        user_id: int | None = None,
        email: str | None = None,
        organization_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        context: AuditContext | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        return self._service.record(
            AuditAction.LOGIN_SUCCESS.value,
            severity=Severity.INFO,
            category=AuditCategory.AUTH,
            status=AuditStatus.SUCCESS,
            success=True,
            message="Connexion réussie",
            actor_user_id=user_id,
            actor_email=email,
            organization_id=organization_id,
            service="auth",
            product="elfis-core",
            ip_address=ip_address,
            user_agent=user_agent,
            context=context,
            metadata=metadata,
        )

    def record_login_failure(
        self,
        *,
        email: str | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        context: AuditContext | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        meta = dict(metadata or {})
        if reason:
            meta["reason"] = reason
        return self._service.record(
            AuditAction.LOGIN_FAILURE.value,
            severity=Severity.WARNING,
            category=AuditCategory.AUTH,
            status=AuditStatus.FAILURE,
            success=False,
            message="Échec de connexion",
            actor_email=email,
            service="auth",
            product="elfis-core",
            ip_address=ip_address,
            user_agent=user_agent,
            context=context,
            metadata=meta,
        )

    def record_logout(
        self,
        *,
        user_id: int | None = None,
        email: str | None = None,
        organization_id: int | None = None,
        ip_address: str | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.LOGOUT.value,
            severity=Severity.INFO,
            category=AuditCategory.AUTH,
            status=AuditStatus.SUCCESS,
            success=True,
            message="Déconnexion",
            actor_user_id=user_id,
            actor_email=email,
            organization_id=organization_id,
            service="auth",
            product="elfis-core",
            ip_address=ip_address,
            context=context,
        )

    def record_role_assignment(
        self,
        *,
        actor_user_id: int | None = None,
        target_user_id: int,
        role_code: str,
        success: bool = True,
        context: AuditContext | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        return self._service.record(
            AuditAction.ROLE_ASSIGNED.value,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.IAM,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            success=success,
            message=f"Rôle plateforme attribué: {role_code}",
            actor_user_id=actor_user_id,
            service="iam",
            product="elfis-core",
            target_type="user",
            target_id=str(target_user_id),
            target_display=f"user:{target_user_id}",
            context=context,
            metadata={**(metadata or {}), "role_code": role_code},
        )

    def record_role_removal(
        self,
        *,
        actor_user_id: int | None = None,
        target_user_id: int,
        role_code: str,
        success: bool = True,
        context: AuditContext | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        return self._service.record(
            AuditAction.ROLE_REMOVED.value,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.IAM,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            success=success,
            message=f"Rôle plateforme retiré: {role_code}",
            actor_user_id=actor_user_id,
            service="iam",
            product="elfis-core",
            target_type="user",
            target_id=str(target_user_id),
            target_display=f"user:{target_user_id}",
            context=context,
            metadata={**(metadata or {}), "role_code": role_code},
        )

    def record_permission_denied(
        self,
        *,
        user_id: int | None = None,
        permission: str | None = None,
        route: str | None = None,
        method: str | None = None,
        organization_id: int | None = None,
        reason: str | None = None,
        correlation_id: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {}
        if permission:
            meta["permission"] = permission
        if route:
            meta["route"] = route
        if method:
            meta["method"] = method
        if reason:
            meta["reason"] = reason
        return self._service.record(
            AuditAction.PERMISSION_DENIED.value,
            severity=Severity.WARNING,
            category=AuditCategory.SECURITY,
            status=AuditStatus.FAILURE,
            success=False,
            message="Permission refusée",
            actor_user_id=user_id,
            organization_id=organization_id,
            service="iam",
            product="elfis-core",
            correlation_id=correlation_id,
            context=context,
            metadata=meta,
        )

    def record_system_health_refresh(
        self,
        *,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        return self._service.record(
            AuditAction.HEALTH_REFRESH.value,
            severity=Severity.INFO,
            category=AuditCategory.SYSTEM,
            status=AuditStatus.SUCCESS,
            success=True,
            message="System Health consulté / rafraîchi",
            actor_user_id=actor_user_id,
            service="system_health",
            product="elfis-core",
            context=context,
            metadata=metadata,
        )

    def record_job_retry(
        self,
        *,
        job_id: str,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.JOB_RETRY.value,
            severity=Severity.INFO,
            category=AuditCategory.JOB,
            success=True,
            message="Retry job",
            actor_user_id=actor_user_id,
            service="jobs",
            target_type="job",
            target_id=job_id,
            context=context,
        )

    def record_event_retry(
        self,
        *,
        event_id: str,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.EVENT_RETRY.value,
            severity=Severity.INFO,
            category=AuditCategory.EVENT,
            success=True,
            message="Retry event",
            actor_user_id=actor_user_id,
            service="events",
            target_type="event",
            target_id=event_id,
            context=context,
        )

    def record_subscription_created(
        self,
        *,
        subscription_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.SUBSCRIPTION_CREATED.value,
            severity=Severity.INFO,
            category=AuditCategory.BILLING,
            success=True,
            message="Abonnement créé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="billing",
            target_type="subscription",
            target_id=subscription_id,
            context=context,
        )

    def record_invoice_import(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.INVOICE_IMPORT.value,
            severity=Severity.INFO,
            category=AuditCategory.COMPTAPILOT,
            success=True,
            message="Import facture",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="comptapilot",
            target_type="document",
            target_id=document_id,
            context=context,
        )

    def record_document_created(
        self,
        *,
        document_id: str,
        storage_object_id: str | None = None,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        source: str | None = None,
        status: str | None = None,
        mime: str | None = None,
        size_bytes: int | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if storage_object_id:
            meta["storage_object_id"] = storage_object_id
        if source:
            meta["source"] = source
        if status:
            meta["status"] = status
        if mime:
            meta["mime"] = mime
        if size_bytes is not None:
            meta["size_bytes"] = size_bytes
        return self._service.record(
            AuditAction.DOCUMENT_CREATED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Document créé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_uploaded(
        self,
        *,
        document_id: str,
        storage_object_id: str | None = None,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        size_bytes: int | None = None,
        mime: str | None = None,
        status: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if storage_object_id:
            meta["storage_object_id"] = storage_object_id
        if size_bytes is not None:
            meta["size_bytes"] = size_bytes
        if mime:
            meta["mime"] = mime
        if status:
            meta["status"] = status
        return self._service.record(
            AuditAction.DOCUMENT_UPLOADED.value,
            severity=Severity.INFO,
            category=AuditCategory.STORAGE,
            success=True,
            message="Fichier uploadé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="storage_object",
            target_id=storage_object_id,
            context=context,
            metadata=meta,
        )

    def record_document_linked(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        relation_type: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if entity_type:
            meta["entity_type"] = entity_type
        if entity_id:
            meta["entity_id"] = entity_id
        if relation_type:
            meta["relation_type"] = relation_type
        return self._service.record(
            AuditAction.DOCUMENT_LINKED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Document lié",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_downloaded(
        self,
        *,
        document_id: str,
        storage_object_id: str | None = None,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        size_bytes: int | None = None,
        mime: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if storage_object_id:
            meta["storage_object_id"] = storage_object_id
        if size_bytes is not None:
            meta["size_bytes"] = size_bytes
        if mime:
            meta["mime"] = mime
        return self._service.record(
            AuditAction.DOCUMENT_DOWNLOADED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Document téléchargé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_archived(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        status: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if status:
            meta["status"] = status
        return self._service.record(
            AuditAction.DOCUMENT_ARCHIVED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Document archivé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_unarchived(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        status: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if status:
            meta["status"] = status
        return self._service.record(
            AuditAction.DOCUMENT_UNARCHIVED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Document désarchivé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_version_created(
        self,
        *,
        document_id: str,
        version_id: str,
        version_number: int,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.DOCUMENT_VERSION_CREATED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Version document créée",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document_version",
            target_id=version_id,
            context=context,
            metadata={
                "document_id": document_id,
                "version_id": version_id,
                "version_number": version_number,
            },
        )

    def record_document_version_superseded(
        self,
        *,
        document_id: str,
        version_id: str,
        version_number: int,
        organization_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.DOCUMENT_VERSION_SUPERSEDED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Version document remplacée",
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document_version",
            target_id=version_id,
            context=context,
            metadata={
                "document_id": document_id,
                "version_id": version_id,
                "version_number": version_number,
            },
        )

    def record_document_version_restored(
        self,
        *,
        document_id: str,
        version_id: str,
        version_number: int,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.DOCUMENT_VERSION_RESTORED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Version document restaurée (nouvelle version)",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document_version",
            target_id=version_id,
            context=context,
            metadata={
                "document_id": document_id,
                "version_id": version_id,
                "version_number": version_number,
            },
        )

    def record_document_soft_deleted(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        reason: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if reason:
            meta["reason"] = str(reason)[:120]
        return self._service.record(
            AuditAction.DOCUMENT_SOFT_DELETED.value,
            severity=Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Document soft-deleted",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_restored(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        status: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if status:
            meta["status"] = status
        return self._service.record(
            AuditAction.DOCUMENT_RESTORED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Document restauré",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_legal_hold_placed(
        self,
        *,
        document_id: str,
        legal_hold_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        reason: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {
            "document_id": document_id,
            "legal_hold_id": legal_hold_id,
        }
        if reason:
            meta["reason"] = str(reason)[:120]
        return self._service.record(
            AuditAction.DOCUMENT_LEGAL_HOLD_PLACED.value,
            severity=Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Legal hold posé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document_legal_hold",
            target_id=legal_hold_id,
            context=context,
            metadata=meta,
        )

    def record_document_legal_hold_released(
        self,
        *,
        document_id: str,
        legal_hold_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.DOCUMENT_LEGAL_HOLD_RELEASED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Legal hold levé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document_legal_hold",
            target_id=legal_hold_id,
            context=context,
            metadata={"document_id": document_id, "legal_hold_id": legal_hold_id},
        )

    def record_document_purge_blocked(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        blocked_reason: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if blocked_reason:
            meta["blocked_reason"] = blocked_reason
        return self._service.record(
            AuditAction.DOCUMENT_PURGE_BLOCKED.value,
            severity=Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=False,
            message="Purge document bloquée",
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_purged(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        document_type: str | None = None,
        storage_object_count: int | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if document_type:
            meta["document_type"] = document_type
        if storage_object_count is not None:
            meta["storage_object_count"] = storage_object_count
        return self._service.record(
            AuditAction.DOCUMENT_PURGED.value,
            severity=Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Document purgé",
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_purge_failed(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        reason: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if reason:
            meta["reason"] = str(reason)[:120]
        return self._service.record(
            AuditAction.DOCUMENT_PURGE_FAILED.value,
            severity=Severity.ERROR,
            category=AuditCategory.DOCUMENT,
            success=False,
            message="Échec purge document",
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_document_purge_requested(
        self,
        *,
        candidate_count: int,
        preview: bool,
        organization_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.DOCUMENT_PURGE_REQUESTED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Demande purge rétention",
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            context=context,
            metadata={"candidate_count": candidate_count, "preview": preview},
        )

    def record_storage_object_rejected(
        self,
        *,
        reason: str | None = None,
        filename: str | None = None,
        size: int | None = None,
        mime: str | None = None,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {}
        if reason:
            meta["reason"] = reason
        if filename:
            # basename seulement déjà attendu — tronquer
            meta["filename"] = str(filename).replace("\\", "/").split("/")[-1][:200]
        if size is not None:
            meta["size_bytes"] = size
        if mime:
            meta["mime"] = mime
        return self._service.record(
            AuditAction.STORAGE_OBJECT_REJECTED.value,
            severity=Severity.WARNING,
            category=AuditCategory.STORAGE,
            status=AuditStatus.FAILURE,
            success=False,
            message="Fichier rejeté",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            context=context,
            metadata=meta,
        )

    def record_storage_object_failed(
        self,
        *,
        reason: str | None = None,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        size: int | None = None,
        mime: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {}
        if reason:
            meta["reason"] = reason
        if size is not None:
            meta["size_bytes"] = size
        if mime:
            meta["mime"] = mime
        return self._service.record(
            AuditAction.STORAGE_OBJECT_FAILED.value,
            severity=Severity.ERROR,
            category=AuditCategory.STORAGE,
            status=AuditStatus.FAILURE,
            success=False,
            message="Échec stockage",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            context=context,
            metadata=meta,
        )

    def record_document_upload_started(
        self,
        *,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        filename: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {}
        if filename:
            meta["filename"] = str(filename).replace("\\", "/").split("/")[-1][:200]
        return self._service.record(
            AuditAction.DOCUMENT_UPLOAD_STARTED.value,
            severity=Severity.INFO,
            category=AuditCategory.STORAGE,
            success=True,
            message="Upload démarré",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            context=context,
            metadata=meta,
        )

    def record_document_upload_completed(
        self,
        *,
        document_id: str,
        storage_object_id: str | None = None,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        size_bytes: int | None = None,
        mime: str | None = None,
        status: str | None = None,
        duration_ms: int | None = None,
        checksum_prefix: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {"document_id": document_id}
        if storage_object_id:
            meta["storage_object_id"] = storage_object_id
        if size_bytes is not None:
            meta["size_bytes"] = size_bytes
        if mime:
            meta["mime"] = mime
        if status:
            meta["status"] = status
        if duration_ms is not None:
            meta["duration_ms"] = duration_ms
        if checksum_prefix:
            meta["checksum_prefix"] = checksum_prefix
        return self._service.record(
            AuditAction.DOCUMENT_UPLOAD_COMPLETED.value,
            severity=Severity.INFO,
            category=AuditCategory.STORAGE,
            success=True,
            message="Upload terminé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
            duration_ms=duration_ms,
        )

    def record_document_upload_failed(
        self,
        *,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        reason: str | None = None,
        duration_ms: int | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {}
        if reason:
            meta["reason"] = str(reason)[:128]
        if duration_ms is not None:
            meta["duration_ms"] = duration_ms
        return self._service.record(
            AuditAction.DOCUMENT_UPLOAD_FAILED.value,
            severity=Severity.WARNING,
            category=AuditCategory.STORAGE,
            status=AuditStatus.FAILURE,
            success=False,
            message="Upload échoué",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            context=context,
            metadata=meta,
            duration_ms=duration_ms,
        )

    def record_document_download_requested(
        self,
        *,
        document_id: str,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.DOCUMENT_DOWNLOAD_REQUESTED.value,
            severity=Severity.INFO,
            category=AuditCategory.DOCUMENT,
            success=True,
            message="Téléchargement demandé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata={"document_id": document_id},
        )

    def record_document_download_denied(
        self,
        *,
        document_id: str | None = None,
        organization_id: int | None = None,
        actor_user_id: int | None = None,
        reason: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {}
        if document_id:
            meta["document_id"] = document_id
        if reason:
            meta["reason"] = reason
        return self._service.record(
            AuditAction.DOCUMENT_DOWNLOAD_DENIED.value,
            severity=Severity.WARNING,
            category=AuditCategory.SECURITY,
            status=AuditStatus.FAILURE,
            success=False,
            message="Téléchargement refusé",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="document",
            target_id=document_id,
            context=context,
            metadata=meta,
        )

    def record_storage_object_quarantined(
        self,
        *,
        storage_object_id: str | None = None,
        organization_id: int | None = None,
        size_bytes: int | None = None,
        mime: str | None = None,
        reason: str | None = None,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {}
        if storage_object_id:
            meta["storage_object_id"] = storage_object_id
        if size_bytes is not None:
            meta["size_bytes"] = size_bytes
        if mime:
            meta["mime"] = mime
        if reason:
            meta["reason"] = reason
        return self._service.record(
            AuditAction.STORAGE_OBJECT_QUARANTINED.value,
            severity=Severity.WARNING,
            category=AuditCategory.STORAGE,
            success=True,
            message="Objet mis en quarantaine",
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="storage_object",
            target_id=storage_object_id,
            context=context,
            metadata=meta,
        )

    def record_storage_object_compensated(
        self,
        *,
        storage_object_id: str | None = None,
        organization_id: int | None = None,
        success: bool = True,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.STORAGE_OBJECT_COMPENSATED.value,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.STORAGE,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            success=success,
            message="Compensation stockage",
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            target_type="storage_object",
            target_id=storage_object_id,
            context=context,
            metadata={"storage_object_id": storage_object_id, "compensated": success},
        )

    def record_storage_object_orphan_detected(
        self,
        *,
        organization_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.STORAGE_OBJECT_ORPHAN_DETECTED.value,
            severity=Severity.WARNING,
            category=AuditCategory.STORAGE,
            success=True,
            message="Orphelin stockage détecté",
            organization_id=organization_id,
            service="storage",
            product="elfis-core",
            context=context,
            metadata=metadata,
        )

    def record_storage_temp_cleanup(
        self,
        *,
        deleted: int,
        preview: bool,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.STORAGE_TEMP_CLEANUP.value,
            severity=Severity.INFO,
            category=AuditCategory.STORAGE,
            success=True,
            message="Nettoyage temporaires storage",
            service="storage",
            product="elfis-core",
            context=context,
            metadata={"deleted": deleted, "preview": preview},
        )

    def _storage_mig(
        self,
        action: str,
        *,
        message: str,
        migration_id: str | None = None,
        storage_object_id: str | None = None,
        checksum_verified: bool | None = None,
        error_code: str | None = None,
        success: bool = True,
        context: AuditContext | None = None,
    ):
        meta: dict[str, Any] = {}
        if migration_id:
            meta["migration_id"] = migration_id
        if storage_object_id:
            meta["storage_object_id"] = storage_object_id
        if checksum_verified is not None:
            meta["checksum_verified"] = checksum_verified
        if error_code:
            meta["error_code"] = error_code
        return self._service.record(
            action,
            severity=Severity.INFO if success else Severity.ERROR,
            category=AuditCategory.STORAGE,
            success=success,
            message=message,
            service="storage",
            product="elfis-core",
            target_type="storage_migration",
            target_id=migration_id,
            context=context,
            metadata=meta,
        )

    def record_storage_migration_started(self, **kwargs):
        return self._storage_mig(
            AuditAction.STORAGE_MIGRATION_STARTED.value, message="Migration storage démarrée", **kwargs
        )

    def record_storage_migration_object_copied(self, **kwargs):
        return self._storage_mig(
            AuditAction.STORAGE_MIGRATION_OBJECT_COPIED.value, message="Objet migré copié", **kwargs
        )

    def record_storage_migration_object_verified(self, **kwargs):
        return self._storage_mig(
            AuditAction.STORAGE_MIGRATION_OBJECT_VERIFIED.value, message="Objet migré vérifié", **kwargs
        )

    def record_storage_migration_object_switched(self, **kwargs):
        return self._storage_mig(
            AuditAction.STORAGE_MIGRATION_OBJECT_SWITCHED.value, message="Objet basculé provider", **kwargs
        )

    def record_storage_migration_failed(self, **kwargs):
        return self._storage_mig(
            AuditAction.STORAGE_MIGRATION_FAILED.value,
            message="Migration storage échouée",
            success=False,
            **kwargs,
        )

    def record_storage_integrity_check_completed(
        self,
        *,
        scanned: int,
        failed: int,
        mode: str,
        preview: bool,
        context: AuditContext | None = None,
    ):
        return self._service.record(
            AuditAction.STORAGE_INTEGRITY_CHECK_COMPLETED.value,
            severity=Severity.INFO if failed == 0 else Severity.WARNING,
            category=AuditCategory.STORAGE,
            success=failed == 0,
            message="Contrôle intégrité storage",
            service="storage",
            product="elfis-core",
            context=context,
            metadata={"scanned": scanned, "failed": failed, "mode": mode, "preview": preview},
        )

    def _dp_event(
        self,
        action: str,
        *,
        message: str,
        job_id: str | None = None,
        document_id: str | None = None,
        version_id: str | None = None,
        organization_id: int | None = None,
        pipeline_key: str | None = None,
        step_key: str | None = None,
        attempt_number: int | None = None,
        duration_ms: int | None = None,
        error_code: str | None = None,
        worker_id: str | None = None,
        success: bool = True,
        actor_user_id: int | None = None,
        context: AuditContext | None = None,
        **_ignore,
    ):
        meta: dict[str, Any] = {}
        for k, v in {
            "job_id": job_id,
            "document_id": document_id,
            "version_id": version_id,
            "pipeline_key": pipeline_key,
            "step_key": step_key,
            "attempt_number": attempt_number,
            "duration_ms": duration_ms,
            "error_code": error_code,
            "worker_id": worker_id,
        }.items():
            if v is not None:
                meta[k] = v
        return self._service.record(
            action,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=success,
            message=message,
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            service="document_processing",
            product="elfis-core",
            target_type="document_processing_job",
            target_id=job_id,
            context=context,
            metadata=meta,
        )

    def record_document_processing_job_created(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_JOB_CREATED.value, message="Job processing créé", **kwargs
        )

    def record_document_processing_job_queued(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_JOB_QUEUED.value, message="Job processing en file", **kwargs
        )

    def record_document_processing_job_started(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_JOB_STARTED.value, message="Job processing démarré", **kwargs
        )

    def record_document_processing_job_completed(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_JOB_COMPLETED.value, message="Job processing terminé", **kwargs
        )

    def record_document_processing_job_failed(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_JOB_FAILED.value,
            message="Job processing échoué",
            success=False,
            **kwargs,
        )

    def record_document_processing_job_cancel_requested(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_JOB_CANCEL_REQUESTED.value,
            message="Annulation job demandée",
            **kwargs,
        )

    def record_document_processing_job_cancelled(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_JOB_CANCELLED.value, message="Job processing annulé", **kwargs
        )

    def record_document_processing_job_retry_requested(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_JOB_RETRY_REQUESTED.value,
            message="Retry job demandé",
            **kwargs,
        )

    def record_document_processing_step_started(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_STEP_STARTED.value, message="Étape processing démarrée", **kwargs
        )

    def record_document_processing_step_completed(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_STEP_COMPLETED.value,
            message="Étape processing terminée",
            **kwargs,
        )

    def record_document_processing_step_failed(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_STEP_FAILED.value,
            message="Étape processing échouée",
            success=False,
            **kwargs,
        )

    def record_document_processing_step_retry_scheduled(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_STEP_RETRY_SCHEDULED.value,
            message="Retry étape planifié",
            **kwargs,
        )

    def record_document_processing_job_lease_recovered(self, **kwargs):
        return self._dp_event(
            AuditAction.DOCUMENT_PROCESSING_JOB_LEASE_RECOVERED.value,
            message="Lease job récupérée",
            **kwargs,
        )

    def _cls_event(self, action: str, *, message: str, success: bool = True, **kwargs):
        classification_id = kwargs.get("classification_id")
        document_id = kwargs.get("document_id")
        version_id = kwargs.get("version_id")
        organization_id = kwargs.get("organization_id")
        meta = {
            k: v
            for k, v in {
                "classification_id": classification_id,
                "document_id": document_id,
                "version_id": version_id,
                "job_id": kwargs.get("job_id"),
                "organization_id": organization_id,
                "classifier_key": kwargs.get("classifier_key"),
                "classifier_version": kwargs.get("classifier_version"),
                "predicted_type": kwargs.get("predicted_type"),
                "confirmed_type": kwargs.get("confirmed_type"),
                "score": kwargs.get("score"),
                "requires_review": kwargs.get("requires_review"),
                "evidence_codes": kwargs.get("evidence_codes"),
            }.items()
            if v is not None
        }
        return self._service.record(
            action,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=success,
            message=message,
            organization_id=organization_id,
            service="document_classification",
            product="elfis-core",
            target_type="document_classification",
            target_id=classification_id or document_id,
            metadata=meta,
        )

    def record_document_classification_started(self, **kwargs):
        return self._cls_event(
            AuditAction.DOCUMENT_CLASSIFICATION_STARTED.value, message="Classification démarrée", **kwargs
        )

    def record_document_classification_proposed(self, **kwargs):
        return self._cls_event(
            AuditAction.DOCUMENT_CLASSIFICATION_PROPOSED.value, message="Classification proposée", **kwargs
        )

    def record_document_classification_confirmed(self, **kwargs):
        return self._cls_event(
            AuditAction.DOCUMENT_CLASSIFICATION_CONFIRMED.value, message="Classification confirmée", **kwargs
        )

    def record_document_classification_rejected(self, **kwargs):
        return self._cls_event(
            AuditAction.DOCUMENT_CLASSIFICATION_REJECTED.value,
            message="Classification rejetée",
            success=False,
            **kwargs,
        )

    def record_document_classification_reclassification_requested(self, **kwargs):
        return self._cls_event(
            AuditAction.DOCUMENT_CLASSIFICATION_RECLASSIFICATION_REQUESTED.value,
            message="Reclassification demandée",
            **kwargs,
        )

    def record_document_classification_failed(self, **kwargs):
        return self._cls_event(
            AuditAction.DOCUMENT_CLASSIFICATION_FAILED.value,
            message="Classification échouée",
            success=False,
            **kwargs,
        )

    def record_document_type_effective_updated(self, **kwargs):
        return self._cls_event(
            AuditAction.DOCUMENT_TYPE_EFFECTIVE_UPDATED.value,
            message="Type documentaire effectif mis à jour",
            **kwargs,
        )

    def _ocr_event(self, action: str, *, message: str, success: bool = True, **kwargs):
        meta = {
            k: v
            for k, v in {
                "ocr_result_id": kwargs.get("ocr_result_id"),
                "document_id": kwargs.get("document_id"),
                "version_id": kwargs.get("version_id"),
                "job_id": kwargs.get("job_id"),
                "organization_id": kwargs.get("organization_id"),
                "provider_key": kwargs.get("provider_key"),
                "provider_version": kwargs.get("provider_version"),
                "extraction_method": kwargs.get("extraction_method"),
                "page_count": kwargs.get("page_count"),
                "text_length": kwargs.get("text_length"),
                "score": kwargs.get("score"),
                "error_code": kwargs.get("error_code"),
                "duration_ms": kwargs.get("duration_ms"),
                "requires_review": kwargs.get("requires_review"),
            }.items()
            if v is not None
        }
        return self._service.record(
            action,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=success,
            message=message,
            actor_user_id=kwargs.get("actor_user_id"),
            organization_id=kwargs.get("organization_id"),
            service="document_ocr",
            product="elfis-core",
            target_type="document_ocr_result",
            target_id=kwargs.get("ocr_result_id") or kwargs.get("document_id"),
            metadata=meta,
        )

    def record_document_ocr_requested(self, **kwargs):
        return self._ocr_event(AuditAction.DOCUMENT_OCR_REQUESTED.value, message="OCR demandé", **kwargs)

    def record_document_ocr_provider_selected(self, **kwargs):
        return self._ocr_event(
            AuditAction.DOCUMENT_OCR_PROVIDER_SELECTED.value, message="Provider OCR sélectionné", **kwargs
        )

    def record_document_ocr_started(self, **kwargs):
        return self._ocr_event(AuditAction.DOCUMENT_OCR_STARTED.value, message="OCR démarré", **kwargs)

    def record_document_ocr_completed(self, **kwargs):
        return self._ocr_event(AuditAction.DOCUMENT_OCR_COMPLETED.value, message="OCR terminé", **kwargs)

    def record_document_ocr_partially_completed(self, **kwargs):
        return self._ocr_event(
            AuditAction.DOCUMENT_OCR_PARTIALLY_COMPLETED.value, message="OCR partiel", **kwargs
        )

    def record_document_ocr_failed(self, **kwargs):
        return self._ocr_event(
            AuditAction.DOCUMENT_OCR_FAILED.value, message="OCR échoué", success=False, **kwargs
        )

    def record_document_ocr_retry_requested(self, **kwargs):
        return self._ocr_event(
            AuditAction.DOCUMENT_OCR_RETRY_REQUESTED.value, message="Retry OCR demandé", **kwargs
        )

    def record_document_ocr_rejected(self, **kwargs):
        return self._ocr_event(
            AuditAction.DOCUMENT_OCR_REJECTED.value, message="OCR rejeté", success=False, **kwargs
        )

    def record_document_ocr_text_accessed(self, **kwargs):
        return self._ocr_event(
            AuditAction.DOCUMENT_OCR_TEXT_ACCESSED.value, message="Texte OCR consulté", **kwargs
        )

    def record_document_ocr_artifact_created(self, **kwargs):
        return self._ocr_event(
            AuditAction.DOCUMENT_OCR_ARTIFACT_CREATED.value, message="Artefact OCR créé", **kwargs
        )

    def record_document_ocr_artifact_deleted(self, **kwargs):
        return self._ocr_event(
            AuditAction.DOCUMENT_OCR_ARTIFACT_DELETED.value, message="Artefact OCR supprimé", **kwargs
        )

    def _extraction_event(self, action: str, *, message: str, success: bool = True, **kwargs):
        props = dict(kwargs)
        meta = {
            k: v
            for k, v in {
                "extraction_result_id": kwargs.get("extraction_result_id"),
                "document_id": kwargs.get("document_id"),
                "version_id": kwargs.get("version_id"),
                "ocr_result_id": kwargs.get("ocr_result_id"),
                "job_id": kwargs.get("job_id"),
                "organization_id": kwargs.get("organization_id"),
                "schema_key": kwargs.get("schema_key"),
                "schema_version": kwargs.get("schema_version"),
                "provider_key": kwargs.get("provider_key"),
                "provider_version": kwargs.get("provider_version"),
                "status": kwargs.get("status"),
                "fields_count": kwargs.get("fields_count"),
                "missing_count": kwargs.get("missing_count"),
                "invalid_count": kwargs.get("invalid_count"),
                "requires_review": kwargs.get("requires_review"),
                "score": kwargs.get("score"),
                "error_code": kwargs.get("error_code"),
                "duration_ms": kwargs.get("duration_ms"),
            }.items()
            if v is not None
        }
        return self._service.record(
            action,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=success,
            message=message,
            actor_user_id=props.get("actor_user_id"),
            organization_id=kwargs.get("organization_id"),
            service="document_extraction",
            product="elfis-core",
            target_type="document_extraction_result",
            target_id=kwargs.get("extraction_result_id") or kwargs.get("document_id"),
            metadata=meta,
        )

    def record_document_extraction_requested(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_REQUESTED.value, message="Extraction demandée", **kwargs
        )

    def record_document_extraction_schema_selected(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_SCHEMA_SELECTED.value, message="Schéma extraction sélectionné", **kwargs
        )

    def record_document_extraction_source_selected(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_SOURCE_SELECTED.value, message="Source extraction sélectionnée", **kwargs
        )

    def record_document_extraction_started(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_STARTED.value, message="Extraction démarrée", **kwargs
        )

    def record_document_extraction_completed(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_COMPLETED.value, message="Extraction terminée", **kwargs
        )

    def record_document_extraction_partially_completed(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_PARTIALLY_COMPLETED.value, message="Extraction partielle", **kwargs
        )

    def record_document_extraction_invalid(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_INVALID.value, message="Extraction invalide", success=False, **kwargs
        )

    def record_document_extraction_failed(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_FAILED.value, message="Extraction échouée", success=False, **kwargs
        )

    def record_document_extraction_confirmed(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_CONFIRMED.value, message="Extraction confirmée", **kwargs
        )

    def record_document_extraction_rejected(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_REJECTED.value, message="Extraction rejetée", success=False, **kwargs
        )

    def record_document_extraction_corrected(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_CORRECTED.value, message="Extraction corrigée", **kwargs
        )

    def record_document_extraction_retry_requested(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_RETRY_REQUESTED.value, message="Retry extraction demandé", **kwargs
        )

    def record_document_extraction_content_accessed(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_CONTENT_ACCESSED.value, message="Contenu extraction consulté", **kwargs
        )

    def record_document_extraction_artifact_created(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_ARTIFACT_CREATED.value, message="Artefact extraction créé", **kwargs
        )

    def record_document_extraction_artifact_deleted(self, **kwargs):
        return self._extraction_event(
            AuditAction.DOCUMENT_EXTRACTION_ARTIFACT_DELETED.value, message="Artefact extraction supprimé", **kwargs
        )

    def _business_validation_event(self, action: str, *, message: str, success: bool = True, **kwargs):
        meta = {
            k: v
            for k, v in {
                "validation_id": kwargs.get("validation_id"),
                "document_id": kwargs.get("document_id"),
                "version_id": kwargs.get("version_id"),
                "extraction_result_id": kwargs.get("extraction_result_id"),
                "organization_id": kwargs.get("organization_id"),
                "job_id": kwargs.get("job_id"),
                "rule_set": kwargs.get("rule_set"),
                "status": kwargs.get("status"),
                "blocking_count": kwargs.get("blocking_count"),
                "warning_count": kwargs.get("warning_count"),
                "issue_code": kwargs.get("issue_code"),
                "resolution_type": kwargs.get("resolution_type"),
                "error_code": kwargs.get("error_code"),
                "actor_user_id": kwargs.get("actor_user_id"),
            }.items()
            if v is not None
        }
        return self._service.record(
            action,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=success,
            message=message,
            actor_user_id=kwargs.get("actor_user_id"),
            organization_id=kwargs.get("organization_id"),
            service="document_business_validation",
            product="elfis-core",
            target_type="document_business_validation",
            target_id=kwargs.get("validation_id") or kwargs.get("document_id"),
            metadata=meta,
        )

    def record_document_business_validation_started(self, **kwargs):
        return self._business_validation_event(
            AuditAction.DOCUMENT_BUSINESS_VALIDATION_STARTED.value, message="Validation métier démarrée", **kwargs
        )

    def record_document_business_validation_completed(self, **kwargs):
        return self._business_validation_event(
            AuditAction.DOCUMENT_BUSINESS_VALIDATION_COMPLETED.value, message="Validation métier terminée", **kwargs
        )

    def record_document_business_validation_invalid(self, **kwargs):
        return self._business_validation_event(
            AuditAction.DOCUMENT_BUSINESS_VALIDATION_INVALID.value,
            message="Validation métier invalide",
            success=False,
            **kwargs,
        )

    def record_document_business_validation_review_required(self, **kwargs):
        return self._business_validation_event(
            AuditAction.DOCUMENT_BUSINESS_VALIDATION_REVIEW_REQUIRED.value,
            message="Validation métier — revue requise",
            **kwargs,
        )

    def record_document_business_validation_confirmed(self, **kwargs):
        return self._business_validation_event(
            AuditAction.DOCUMENT_BUSINESS_VALIDATION_CONFIRMED.value, message="Validation métier confirmée", **kwargs
        )

    def record_document_validation_issue_resolved(self, **kwargs):
        return self._business_validation_event(
            AuditAction.DOCUMENT_VALIDATION_ISSUE_RESOLVED.value, message="Issue validation résolue", **kwargs
        )

    def _product_integration_event(self, action: str, *, message: str, success: bool = True, **kwargs):
        meta = {
            k: v
            for k, v in {
                "package_id": kwargs.get("package_id"),
                "delivery_id": kwargs.get("delivery_id"),
                "document_id": kwargs.get("document_id"),
                "version_id": kwargs.get("version_id"),
                "extraction_result_id": kwargs.get("extraction_result_id"),
                "validation_id": kwargs.get("validation_id"),
                "organization_id": kwargs.get("organization_id"),
                "product_key": kwargs.get("product_key"),
                "bridge_version": kwargs.get("bridge_version"),
                "status": kwargs.get("status"),
                "attempt_number": kwargs.get("attempt_number"),
                "duration_ms": kwargs.get("duration_ms"),
                "error_code": kwargs.get("error_code"),
                "external_reference": kwargs.get("external_reference"),
                "actor_user_id": kwargs.get("actor_user_id"),
            }.items()
            if v is not None
        }
        return self._service.record(
            action,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.DOCUMENT,
            success=success,
            message=message,
            actor_user_id=kwargs.get("actor_user_id"),
            organization_id=kwargs.get("organization_id"),
            service="product_integrations",
            product="elfis-core",
            target_type="product_document_package",
            target_id=kwargs.get("package_id") or kwargs.get("delivery_id") or kwargs.get("document_id"),
            metadata=meta,
        )

    def record_product_document_package_created(self, **kwargs):
        return self._product_integration_event(
            AuditAction.PRODUCT_DOCUMENT_PACKAGE_CREATED.value, message="Package produit créé", **kwargs
        )

    def record_product_document_package_ready(self, **kwargs):
        return self._product_integration_event(
            AuditAction.PRODUCT_DOCUMENT_PACKAGE_READY.value, message="Package produit prêt", **kwargs
        )

    def record_product_document_delivery_queued(self, **kwargs):
        return self._product_integration_event(
            AuditAction.PRODUCT_DOCUMENT_DELIVERY_QUEUED.value, message="Livraison produit en file", **kwargs
        )

    def record_product_document_delivery_started(self, **kwargs):
        return self._product_integration_event(
            AuditAction.PRODUCT_DOCUMENT_DELIVERY_STARTED.value, message="Livraison produit démarrée", **kwargs
        )

    def record_product_document_delivery_completed(self, **kwargs):
        return self._product_integration_event(
            AuditAction.PRODUCT_DOCUMENT_DELIVERY_COMPLETED.value, message="Livraison produit terminée", **kwargs
        )

    def record_product_document_delivery_failed(self, **kwargs):
        return self._product_integration_event(
            AuditAction.PRODUCT_DOCUMENT_DELIVERY_FAILED.value,
            message="Livraison produit échouée",
            success=False,
            **kwargs,
        )

    def record_product_document_delivery_retry_requested(self, **kwargs):
        return self._product_integration_event(
            AuditAction.PRODUCT_DOCUMENT_DELIVERY_RETRY_REQUESTED.value,
            message="Retry livraison demandé",
            **kwargs,
        )

    def record_comptapilot_document_publish_requested(self, **kwargs):
        return self._product_integration_event(
            AuditAction.COMPTAPILOT_DOCUMENT_PUBLISH_REQUESTED.value,
            message="Publication ComptaPilot demandée",
            **kwargs,
        )

    def record_comptapilot_document_published(self, **kwargs):
        return self._product_integration_event(
            AuditAction.COMPTAPILOT_DOCUMENT_PUBLISHED.value, message="Document publié vers ComptaPilot", **kwargs
        )

    def record_comptapilot_document_publish_failed(self, **kwargs):
        return self._product_integration_event(
            AuditAction.COMPTAPILOT_DOCUMENT_PUBLISH_FAILED.value,
            message="Publication ComptaPilot échouée",
            success=False,
            **kwargs,
        )

    def _migration_center_event(self, action: str, *, message: str, success: bool = True, **kwargs):
        meta = {
            k: v
            for k, v in {
                "session_id": kwargs.get("session_id"),
                "mode": kwargs.get("mode"),
                "old_status": kwargs.get("old_status"),
                "new_status": kwargs.get("new_status"),
                "current_step": kwargs.get("current_step"),
                "source_count": kwargs.get("source_count"),
                "actor_user_id": kwargs.get("actor_user_id"),
            }.items()
            if v is not None
        }
        return self._service.record(
            action,
            severity=Severity.INFO if success else Severity.WARNING,
            category=AuditCategory.SECURITY if not success else AuditCategory.DOCUMENT,
            success=success,
            message=message,
            actor_user_id=kwargs.get("actor_user_id"),
            organization_id=kwargs.get("organization_id"),
            service="migration_center",
            product="elfis-core",
            target_type="migration_session",
            target_id=kwargs.get("session_id"),
            metadata=meta,
        )

    def record_migration_session_created(self, **kwargs):
        return self._migration_center_event(
            AuditAction.MIGRATION_SESSION_CREATED.value,
            message="Session de migration créée",
            **kwargs,
        )

    def record_migration_profile_updated(self, **kwargs):
        return self._migration_center_event(
            AuditAction.MIGRATION_PROFILE_UPDATED.value,
            message="Profil entreprise migration mis à jour",
            **kwargs,
        )

    def record_migration_sources_updated(self, **kwargs):
        return self._migration_center_event(
            AuditAction.MIGRATION_SOURCES_UPDATED.value,
            message="Sources de migration mises à jour",
            **kwargs,
        )

    def record_migration_step_completed(self, **kwargs):
        return self._migration_center_event(
            AuditAction.MIGRATION_STEP_COMPLETED.value,
            message="Étape de migration validée",
            **kwargs,
        )

    def record_migration_session_cancelled(self, **kwargs):
        return self._migration_center_event(
            AuditAction.MIGRATION_SESSION_CANCELLED.value,
            message="Session de migration annulée",
            success=False,
            **kwargs,
        )
