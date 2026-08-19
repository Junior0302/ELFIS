"""Service d'audit administratif enrichi (+ bridge write_audit legacy)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models_saas import User
from app.platform_admin.admin_logging import hash_ip, sanitize_admin_text
from app.platform_admin.admin_models import ElfisAdminAuditLog
from app.platform_admin.admin_security import filter_state_dict
from app.platform_admin.admin_types import AdminAuditStatus


class AdminAuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        actor: User,
        action: str,
        target_type: str,
        target_id: str | None = None,
        organization_id: int | None = None,
        reason: str | None = None,
        previous_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
        status: str = AdminAuditStatus.SUCCEEDED,
        error_code: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        legacy_module: str = "platform_admin",
    ) -> ElfisAdminAuditLog:
        row = ElfisAdminAuditLog(
            id=str(uuid4()),
            audit_id=str(uuid4()),
            actor_user_id=actor.id,
            actor_email=actor.email,
            organization_id=organization_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            reason=sanitize_admin_text(reason, max_len=2000),
            previous_state=filter_state_dict(previous_state),
            new_state=filter_state_dict(new_state),
            request_id=request_id,
            correlation_id=correlation_id,
            ip_hash=hash_ip(ip),
            user_agent_summary=(user_agent or "")[:255] or None,
            status=status,
            error_code=error_code,
            created_at=datetime.utcnow(),
        )
        self.db.add(row)
        # Bridge legacy audit_logs (sans commit forcé)
        from app.models_saas import AuditLog

        self.db.add(
            AuditLog(
                user_id=actor.id,
                organization_id=organization_id,
                action=f"elfadmin.{action}:{target_id or ''}",
                module=legacy_module,
                ip=ip or "",
            )
        )
        self.db.flush()
        return row

    def list_audits(
        self,
        *,
        actor_user_id: int | None = None,
        organization_id: int | None = None,
        action: str | None = None,
        target_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[ElfisAdminAuditLog], int]:
        q = self.db.query(ElfisAdminAuditLog)
        if actor_user_id:
            q = q.filter(ElfisAdminAuditLog.actor_user_id == actor_user_id)
        if organization_id:
            q = q.filter(ElfisAdminAuditLog.organization_id == organization_id)
        if action:
            q = q.filter(ElfisAdminAuditLog.action == action)
        if target_type:
            q = q.filter(ElfisAdminAuditLog.target_type == target_type)
        if status:
            q = q.filter(ElfisAdminAuditLog.status == status)
        total = q.count()
        rows = (
            q.order_by(ElfisAdminAuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total
