"""Exécution d’actions Decision Center — délégation aux services métier."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounting.accounting_exceptions import (
    AccountingPermissionError,
    AccountingStateError,
    AccountingValidationError,
)
from app.accounting.accounting_schemas import AccountingValidationRequest
from app.accounting.accounting_security import check_accounting_permission
from app.accounting.accounting_service import AccountingService
from app.ai.ai_exceptions import AINotFoundError
from app.ai.document_analysis_service import DocumentAnalysisService
from app.decision_center.actions import build_available_actions
from app.decision_center.enums import (
    DecisionActionType,
    DecisionExecutionAttemptStatus,
    DecisionExecutionStatus,
    DecisionStatus,
)
from app.decision_center.models import ElfisDecisionExecutionAttempt, ElfisDecisionItem
from app.decision_center.schemas import (
    DecisionExecuteOut,
    DecisionExecuteRequest,
    DecisionExecuteResultOut,
)
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.services.auth import write_audit

logger = logging.getLogger(__name__)


class DecisionExecutionService:
    def __init__(self, db: Session, decision_service: Any):
        self.db = db
        self.decisions = decision_service

    def execute(
        self,
        *,
        organization_id: int,
        decision_id: str,
        action_type: str,
        permissions: list[str],
        user_id: int | None,
        body: DecisionExecuteRequest | None = None,
    ) -> DecisionExecuteOut:
        body = body or DecisionExecuteRequest()
        row = self.decisions.repo.get(organization_id=organization_id, decision_id=decision_id)
        if row is None:
            raise HTTPException(404, detail="Décision introuvable")
        if not self.decisions._can_view(row, permissions):
            raise HTTPException(403, detail="Permission insuffisante")

        if row.status == DecisionStatus.RESOLVED:
            raise HTTPException(409, detail="Cette décision a déjà été résolue.")
        if row.status == DecisionStatus.DISMISSED:
            raise HTTPException(409, detail="Cette décision a été ignorée.")
        if row.status == DecisionStatus.EXPIRED:
            raise HTTPException(409, detail="Cette décision a expiré.")
        if row.status not in {DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS}:
            raise HTTPException(409, detail="Cette action n’est plus autorisée dans l’état actuel.")

        if row.execution_status == DecisionExecutionStatus.RUNNING:
            raise HTTPException(409, detail="Une action est déjà en cours pour cette décision.")

        source = self.decisions.load_source(row)
        actions = build_available_actions(
            row=row,
            permissions=permissions,
            allows=self.decisions._allows,
            source=source,
        )
        match = next((a for a in actions if a.action_type == action_type), None)
        if match is None:
            raise HTTPException(400, detail="Action non déclarée pour cette décision.")
        if not match.enabled:
            raise HTTPException(
                409,
                detail=match.disabled_reason or "Cette action n’est plus autorisée dans l’état actuel.",
            )

        if action_type == DecisionActionType.DISMISS:
            dismissed = self.decisions.dismiss(
                organization_id=organization_id,
                decision_id=decision_id,
                permissions=permissions,
                user_id=user_id,
            )
            detail = self.decisions.get_detail(
                organization_id=organization_id,
                decision_id=decision_id,
                permissions=permissions,
                sync=False,
            )
            return DecisionExecuteOut(
                decision=detail,
                result=DecisionExecuteResultOut(
                    action_type=action_type,
                    status="succeeded",
                    message="Décision ignorée.",
                ),
            )

        if match.method == "NAVIGATE":
            # Trace consultation légère sans changer le statut métier
            attempt = self._start_attempt(
                row=row,
                user_id=user_id,
                action_type=action_type,
                idempotency_key=body.idempotency_key,
            )
            self._finish_attempt(attempt, status=DecisionExecutionAttemptStatus.SUCCEEDED)
            row.last_action_type = action_type
            row.last_action_by_user_id = user_id
            row.execution_status = DecisionExecutionStatus.SUCCEEDED
            row.execution_completed_at = datetime.utcnow()
            if row.status == DecisionStatus.OPEN:
                row.status = DecisionStatus.IN_PROGRESS
            self.db.add(row)
            self.db.commit()
            detail = self.decisions.get_detail(
                organization_id=organization_id,
                decision_id=decision_id,
                permissions=permissions,
                sync=False,
            )
            return DecisionExecuteOut(
                decision=detail,
                result=DecisionExecuteResultOut(
                    execution_id=attempt.id,
                    action_type=action_type,
                    status="succeeded",
                    navigation_path=match.action_path,
                    message="Ouverture de la ressource.",
                ),
            )

        # Idempotence : retourner la tentative existante
        if body.idempotency_key:
            existing = (
                self.db.query(ElfisDecisionExecutionAttempt)
                .filter(
                    ElfisDecisionExecutionAttempt.organization_id == organization_id,
                    ElfisDecisionExecutionAttempt.decision_id == decision_id,
                    ElfisDecisionExecutionAttempt.action_type == action_type,
                    ElfisDecisionExecutionAttempt.idempotency_key == body.idempotency_key,
                )
                .one_or_none()
            )
            if existing is not None:
                detail = self.decisions.get_detail(
                    organization_id=organization_id,
                    decision_id=decision_id,
                    permissions=permissions,
                    sync=True,
                )
                return DecisionExecuteOut(
                    decision=detail,
                    result=DecisionExecuteResultOut(
                        execution_id=existing.id,
                        action_type=action_type,
                        status=existing.status,
                        message="Résultat d’une requête déjà traitée.",
                        error_code=existing.error_code,
                    ),
                )

        attempt = self._start_attempt(
            row=row,
            user_id=user_id,
            action_type=action_type,
            idempotency_key=body.idempotency_key,
        )
        self._publish_execution(EventNames.DECISION_EXECUTION_STARTED, row, attempt)

        try:
            result_payload = self._run_business_action(
                row=row,
                action_type=action_type,
                permissions=permissions,
                user_id=user_id,
                body=body,
                source=source,
            )
        except HTTPException as exc:
            self._fail_attempt(row, attempt, code="http_error", message=str(exc.detail))
            raise
        except (AccountingPermissionError,) as exc:
            self._fail_attempt(row, attempt, code="permission_denied", message=exc.message)
            raise HTTPException(403, detail=exc.message) from exc
        except (AccountingValidationError, AccountingStateError) as exc:
            self._fail_attempt(row, attempt, code="business_error", message=exc.message)
            raise HTTPException(409, detail=exc.message) from exc
        except AINotFoundError as exc:
            self._fail_attempt(row, attempt, code="source_missing", message=str(exc.message))
            raise HTTPException(404, detail="La ressource associée n’est plus disponible.") from exc
        except Exception:
            logger.exception("decision_execution_failed id=%s action=%s", row.id, action_type)
            self._fail_attempt(
                row,
                attempt,
                code="internal_error",
                message="L’action n’a pas pu être terminée. Réessayez plus tard.",
            )
            raise HTTPException(
                500, detail="L’action n’a pas pu être terminée. Réessayez plus tard."
            ) from None

        self._finish_attempt(attempt, status=DecisionExecutionAttemptStatus.SUCCEEDED)
        row.execution_status = DecisionExecutionStatus.SUCCEEDED
        row.execution_completed_at = datetime.utcnow()
        row.execution_failed_at = None
        row.last_execution_error_code = None
        row.last_execution_error_message = None
        row.last_action_type = action_type
        row.last_action_by_user_id = user_id
        if row.status == DecisionStatus.OPEN:
            row.status = DecisionStatus.IN_PROGRESS
        self.db.add(row)
        self.db.flush()

        # Resync : résolution uniquement si la cause a disparu
        self.decisions.sync_open_decisions(organization_id)
        self.db.refresh(row)

        write_audit(
            self.db,
            user_id=user_id,
            organization_id=organization_id,
            action=f"decision.execute:{row.id}:{action_type}",
            module="decision_center",
        )
        self._publish_execution(EventNames.DECISION_EXECUTION_SUCCEEDED, row, attempt)
        self.db.commit()

        detail = self.decisions.get_detail(
            organization_id=organization_id,
            decision_id=decision_id,
            permissions=permissions,
            sync=False,
        )
        return DecisionExecuteOut(
            decision=detail,
            result=DecisionExecuteResultOut(
                execution_id=attempt.id,
                action_type=action_type,
                status="succeeded",
                message=result_payload.get("message"),
                navigation_path=result_payload.get("navigation_path"),
                source_status=result_payload.get("source_status"),
            ),
        )

    def _run_business_action(
        self,
        *,
        row: ElfisDecisionItem,
        action_type: str,
        permissions: list[str],
        user_id: int | None,
        body: DecisionExecuteRequest,
        source: Any | None,
    ) -> dict[str, Any]:
        if action_type == DecisionActionType.VALIDATE_ACCOUNTING_PROPOSAL:
            check_accounting_permission(permissions, "validate")
            if user_id is None:
                raise HTTPException(401, detail="Authentification requise")
            AccountingService(self.db).validate_proposal(
                organization_id=row.organization_id,
                proposal_id=row.source_id,
                user_id=user_id,
                body=AccountingValidationRequest(
                    comment=body.comment,
                    confirm_balanced_entry=body.confirm_balanced_entry,
                    confirm_document_reviewed=body.confirm_document_reviewed,
                ),
            )
            return {
                "message": "Proposition validée. La décision sera résolue si la cause a disparu.",
                "navigation_path": f"/accounting/proposals/{row.source_id}",
                "source_status": "validated",
            }

        if action_type == DecisionActionType.RETRY_DOCUMENT_ANALYSIS:
            if not (
                self.decisions._allows(permissions, "ai.analysis")
                or self.decisions._allows(permissions, "documents.write")
            ):
                raise HTTPException(403, detail="Permission insuffisante")
            vault_id = getattr(source, "vault_document_id", None) if source else None
            if not vault_id:
                raise HTTPException(409, detail="Référence document manquante — relance impossible.")
            accepted = DocumentAnalysisService(self.db).start_analysis(
                organization_id=row.organization_id,
                user_id=user_id,
                vault_document_id=str(vault_id),
            )
            return {
                "message": "Analyse relancée."
                if not accepted.reused_existing_analysis
                else "Une analyse existante a été réutilisée.",
                "navigation_path": f"/documents?document_id={vault_id}",
                "source_status": accepted.status,
            }

        raise HTTPException(400, detail="Action d’exécution non supportée.")

    def _start_attempt(
        self,
        *,
        row: ElfisDecisionItem,
        user_id: int | None,
        action_type: str,
        idempotency_key: str | None,
    ) -> ElfisDecisionExecutionAttempt:
        now = datetime.utcnow()
        attempt = ElfisDecisionExecutionAttempt(
            id=str(uuid4()),
            organization_id=row.organization_id,
            decision_id=row.id,
            user_id=user_id,
            action_type=action_type,
            status=DecisionExecutionAttemptStatus.RUNNING,
            idempotency_key=idempotency_key,
            started_at=now,
            metadata_json={"source_type": row.source_type, "source_id": row.source_id},
        )
        row.execution_status = DecisionExecutionStatus.RUNNING
        row.execution_started_at = now
        row.execution_attempts = int(row.execution_attempts or 0) + 1
        row.updated_at = now
        self.db.add(attempt)
        self.db.add(row)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                409, detail="Une requête identique est déjà en cours ou a été traitée."
            ) from exc
        return attempt

    def _finish_attempt(
        self, attempt: ElfisDecisionExecutionAttempt, *, status: str
    ) -> None:
        attempt.status = status
        attempt.completed_at = datetime.utcnow()
        self.db.add(attempt)
        self.db.flush()

    def _fail_attempt(
        self,
        row: ElfisDecisionItem,
        attempt: ElfisDecisionExecutionAttempt,
        *,
        code: str,
        message: str,
    ) -> None:
        safe_msg = (message or "")[:500]
        attempt.status = DecisionExecutionAttemptStatus.FAILED
        attempt.error_code = code
        attempt.error_message = safe_msg
        attempt.completed_at = datetime.utcnow()
        row.execution_status = DecisionExecutionStatus.FAILED
        row.execution_failed_at = datetime.utcnow()
        row.last_execution_error_code = code
        row.last_execution_error_message = safe_msg
        row.last_action_type = attempt.action_type
        self.db.add(attempt)
        self.db.add(row)
        self._publish_execution(EventNames.DECISION_EXECUTION_FAILED, row, attempt)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _publish_execution(
        self, event_name: str, row: ElfisDecisionItem, attempt: ElfisDecisionExecutionAttempt
    ) -> None:
        try:
            safe_publish(
                self.db,
                DomainEvent(
                    event_name=event_name,
                    organization_id=row.organization_id,
                    aggregate_type="decision_execution",
                    aggregate_id=attempt.id,
                    payload={
                        "decision_id": row.id,
                        "execution_id": attempt.id,
                        "action_type": attempt.action_type,
                        "status": attempt.status,
                        "source_type": row.source_type,
                        "source_id": row.source_id,
                        "error_code": attempt.error_code,
                    },
                    idempotency_key=f"{event_name}:{attempt.id}:{attempt.status}",
                ),
            )
        except Exception:
            logger.exception("decision_execution_event_failed id=%s", attempt.id)
