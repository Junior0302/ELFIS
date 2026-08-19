"""Façade Platform Admin."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.platform_admin.admin_audit_service import AdminAuditService
from app.platform_admin.admin_dashboard_service import AdminDashboardService
from app.platform_admin.admin_health_service import AdminHealthService
from app.platform_admin.admin_incident_service import AdminIncidentService
from app.platform_admin.admin_operations_service import AdminOperationsService
from app.platform_admin.admin_organization_service import AdminOrganizationService


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.dashboard = AdminDashboardService(db)
        self.health = AdminHealthService(db)
        self.organizations = AdminOrganizationService(db)
        self.operations = AdminOperationsService(db)
        self.incidents = AdminIncidentService(db)
        self.audit = AdminAuditService(db)
