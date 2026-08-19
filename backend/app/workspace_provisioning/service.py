"""Orchestrateur Workspace Provisioning V1."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models_saas import Organization
from app.services.auth import write_audit
from app.workspace_provisioning import events as provision_events
from app.workspace_provisioning.models import WorkspaceProvisioningRun
from app.workspace_provisioning.schemas import (
    WorkspaceProvisionRequest,
    WorkspaceProvisionStatusOut,
)
from app.workspace_provisioning.steps import (
    PROGRESS_BY_STEP,
    PROVISIONING_VERSION,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    STEP_COMPLETED,
    STEP_COMPLETING,
    STEP_CONFIGURING,
    STEP_SAVING_PROFILE,
    STEP_VALIDATING,
)

logger = logging.getLogger(__name__)


def _defaults_for_country(country: str) -> tuple[str, str]:
    if country == "FR":
        return "fr-FR", "Europe/Paris"
    if country in {"BE", "LU", "CH"}:
        return "fr-FR", "Europe/Paris"
    return "en-US", "UTC"


class WorkspaceProvisioningService:
    """Source de vérité backend pour l’initialisation du workspace."""

    def __init__(self, db: Session):
        self.db = db

    def get_status(self, organization_id: int) -> WorkspaceProvisionStatusOut:
        org = self.db.get(Organization, organization_id)
        if org is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ORGANIZATION_NOT_FOUND",
                    "message": "Organisation introuvable.",
                },
            )
        run = self._get_run(organization_id)
        setup_completed = bool(getattr(org, "setup_completed", False))
        if run is None:
            if setup_completed:
                return WorkspaceProvisionStatusOut.from_run(
                    status=STATUS_COMPLETED,
                    current_step=STEP_COMPLETED,
                    progress=100,
                    setup_completed=True,
                    completed_at=getattr(org, "setup_completed_at", None),
                    provisioning_version=int(getattr(org, "setup_version", 0) or PROVISIONING_VERSION),
                )
            return WorkspaceProvisionStatusOut.from_run(
                status=STATUS_PENDING,
                current_step=STATUS_PENDING,
                progress=0,
                setup_completed=False,
            )
        return WorkspaceProvisionStatusOut.from_run(
            status=run.status,
            current_step=run.current_step,
            progress=run.progress,
            setup_completed=setup_completed or run.status == STATUS_COMPLETED,
            error_code=run.error_code,
            error_message_safe=run.error_message_safe,
            started_at=run.started_at,
            completed_at=run.completed_at,
            provisioning_version=run.provisioning_version,
        )

    def provision(
        self,
        *,
        organization_id: int,
        user_id: int,
        payload: WorkspaceProvisionRequest,
        ip: str | None = None,
    ) -> WorkspaceProvisionStatusOut:
        org = self.db.get(Organization, organization_id)
        if org is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ORGANIZATION_NOT_FOUND",
                    "message": "Organisation introuvable.",
                },
            )
        if getattr(org, "platform_status", "active") not in {"active", None, ""}:
            if getattr(org, "platform_status", "active") != "active":
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "PROVISIONING_FORBIDDEN",
                        "message": "Cette organisation ne peut pas être configurée.",
                    },
                )

        run = self._get_or_create_run(organization_id)

        if run.status == STATUS_COMPLETED or bool(getattr(org, "setup_completed", False)):
            return self.get_status(organization_id)

        try:
            return self._run_pipeline(
                org=org,
                run=run,
                user_id=user_id,
                payload=payload,
                ip=ip,
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception(
                "workspace_provision_failed",
                extra={"organization_id": organization_id, "user_id": user_id},
            )
            self.db.rollback()
            run = self._get_or_create_run(organization_id)
            run.status = STATUS_FAILED
            run.current_step = run.current_step or STEP_VALIDATING
            run.error_code = "PROVISIONING_FAILED"
            run.error_message_safe = (
                "La préparation de votre espace a échoué. Vous pouvez réessayer."
            )
            run.updated_at = datetime.utcnow()
            self.db.add(run)
            try:
                provision_events.publish_provision_event(
                    self.db,
                    event_name=provision_events.EVENT_FAILED,
                    organization_id=organization_id,
                    user_id=user_id,
                    step=run.current_step,
                    idempotency_key=f"provision-failed-{organization_id}-{run.id}",
                )
            except Exception:  # noqa: BLE001
                pass
            self.db.commit()
            return self.get_status(organization_id)

    def _run_pipeline(
        self,
        *,
        org: Organization,
        run: WorkspaceProvisioningRun,
        user_id: int,
        payload: WorkspaceProvisionRequest,
        ip: str | None,
    ) -> WorkspaceProvisionStatusOut:
        now = datetime.utcnow()
        run.status = STATUS_RUNNING
        run.error_code = ""
        run.error_message_safe = ""
        run.started_at = run.started_at or now
        run.updated_at = now
        run.provisioning_version = PROVISIONING_VERSION
        self._set_step(run, STEP_VALIDATING)
        self.db.add(run)
        self.db.flush()

        provision_events.publish_provision_event(
            self.db,
            event_name=provision_events.EVENT_STARTED,
            organization_id=org.id,
            user_id=user_id,
            step=STEP_VALIDATING,
            idempotency_key=f"provision-started-{org.id}-v{PROVISIONING_VERSION}",
        )

        # validating_setup — schéma déjà validé par Pydantic ; step explicite
        self._set_step(run, STEP_VALIDATING)
        self.db.flush()

        self._set_step(run, STEP_SAVING_PROFILE)
        self._save_company_profile(org, payload)
        self.db.flush()
        provision_events.publish_provision_event(
            self.db,
            event_name=provision_events.EVENT_PROFILE,
            organization_id=org.id,
            user_id=user_id,
            step=STEP_SAVING_PROFILE,
            idempotency_key=f"provision-profile-{org.id}-v{PROVISIONING_VERSION}",
        )

        self._set_step(run, STEP_CONFIGURING)
        self._configure_workspace(org, payload.country)
        self.db.flush()
        provision_events.publish_provision_event(
            self.db,
            event_name=provision_events.EVENT_SETTINGS,
            organization_id=org.id,
            user_id=user_id,
            step=STEP_CONFIGURING,
            idempotency_key=f"provision-settings-{org.id}-v{PROVISIONING_VERSION}",
        )

        self._set_step(run, STEP_COMPLETING)
        org.setup_completed = True
        org.setup_completed_at = datetime.utcnow()
        org.setup_version = PROVISIONING_VERSION
        self.db.add(org)
        self.db.flush()

        run.status = STATUS_COMPLETED
        run.completed_at = datetime.utcnow()
        self._set_step(run, STEP_COMPLETED)
        self.db.add(run)

        provision_events.publish_provision_event(
            self.db,
            event_name=provision_events.EVENT_COMPLETED,
            organization_id=org.id,
            user_id=user_id,
            step=STEP_COMPLETED,
            idempotency_key=f"provision-completed-{org.id}-v{PROVISIONING_VERSION}",
        )

        try:
            write_audit(
                self.db,
                user_id=user_id,
                organization_id=org.id,
                action="workspace.provision.completed",
                module="organisation",
                ip=ip,
            )
        except Exception:  # noqa: BLE001
            logger.warning("workspace_provision_audit_failed", exc_info=True)

        self.db.commit()
        self.db.refresh(org)
        self.db.refresh(run)
        return self.get_status(org.id)

    def _save_company_profile(self, org: Organization, payload: WorkspaceProvisionRequest) -> None:
        org.name = payload.company_name
        if not (org.legal_name or "").strip():
            org.legal_name = payload.company_name
        org.industry = payload.industry
        org.industry_other = payload.industry_other or ""
        org.country = payload.country
        org.currency = payload.currency
        org.vat_status = payload.vat_status
        if payload.vat_status == "vat_registered":
            org.vat_number = payload.vat_number or ""
        # ne pas effacer un vat_number existant si statut unknown / not_registered ? Spec: conserver uniquement si pertinent
        else:
            # laisser l’ancien numéro si déjà présent ? Spec: vat_number only if applicable — clear when not registered
            org.vat_number = ""
        self.db.add(org)

    def _configure_workspace(self, org: Organization, country: str) -> None:
        locale_default, tz_default = _defaults_for_country(country)
        current_locale = (getattr(org, "locale", None) or "").strip()
        current_tz = (getattr(org, "timezone", None) or "").strip()
        if not current_locale:
            org.locale = locale_default
        if not current_tz:
            org.timezone = tz_default
        # country/currency déjà posés sur le profil — source unique Organization
        self.db.add(org)
        # SalesPilot: pipeline commercial par défaut (idempotent)
        try:
            from app.sales_crm.service import ensure_default_pipeline

            ensure_default_pipeline(self.db, organization_id=org.id, user_id=None)
        except Exception:  # noqa: BLE001
            logger.warning("sales_default_pipeline_provision_failed", exc_info=True)

    def _set_step(self, run: WorkspaceProvisioningRun, step: str) -> None:
        run.current_step = step
        run.progress = int(PROGRESS_BY_STEP.get(step, run.progress))
        run.updated_at = datetime.utcnow()
        self.db.add(run)

    def _get_run(self, organization_id: int) -> WorkspaceProvisioningRun | None:
        return (
            self.db.query(WorkspaceProvisioningRun)
            .filter(WorkspaceProvisioningRun.organization_id == organization_id)
            .one_or_none()
        )

    def _get_or_create_run(self, organization_id: int) -> WorkspaceProvisioningRun:
        run = self._get_run(organization_id)
        if run is not None:
            return run
        run = WorkspaceProvisioningRun(
            organization_id=organization_id,
            status=STATUS_PENDING,
            current_step=STATUS_PENDING,
            progress=0,
            provisioning_version=PROVISIONING_VERSION,
        )
        try:
            with self.db.begin_nested():
                self.db.add(run)
                self.db.flush()
        except IntegrityError:
            existing = self._get_run(organization_id)
            if existing is None:
                raise
            return existing
        return run
