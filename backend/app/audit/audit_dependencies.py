"""Dépendances FastAPI — Audit Engine (lecture admin)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.audit.audit_service import AuditService
from app.database import get_db
from app.iam.permission_catalog import Permission
from app.iam.permission_dependencies import require_permission

require_audit_read = require_permission(Permission.SECURITY_AUDIT_READ.value)
require_audit_export = require_permission(Permission.SECURITY_AUDIT_EXPORT.value)
require_audit_retention_read = require_permission(Permission.SECURITY_AUDIT_RETENTION_READ.value)
require_audit_retention_manage = require_permission(Permission.SECURITY_AUDIT_RETENTION_MANAGE.value)


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    # Lectures sur la session requête ; écritures isolées par défaut
    return AuditService(db, isolated_writes=True)
