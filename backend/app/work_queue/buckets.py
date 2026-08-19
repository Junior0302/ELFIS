"""Mapping déterministe Decision → Work Queue bucket."""

from __future__ import annotations

from typing import Any

from app.decision_center.enums import (
    DecisionActionType,
    DecisionExecutionStatus,
    DecisionStatus,
)
from app.work_queue.enums import WaitingReasonCode, WorkQueueBucket


def resolve_work_queue_bucket(row: Any) -> WorkQueueBucket:
    """
    Une décision appartient à un seul bucket.

    Ordre :
    1. resolved / dismissed / expired → completed
    2. execution pending/running → in_progress
    3. status in_progress → in_progress
    4. open + retry analyse réussie (cause encore présente) → waiting
    5. open → todo
    """
    status = getattr(row, "status", None) or ""
    exec_status = getattr(row, "execution_status", None) or DecisionExecutionStatus.IDLE
    last_action = getattr(row, "last_action_type", None) or ""

    if status in {
        DecisionStatus.RESOLVED,
        DecisionStatus.DISMISSED,
        DecisionStatus.EXPIRED,
    }:
        return WorkQueueBucket.COMPLETED

    if exec_status in {DecisionExecutionStatus.PENDING, DecisionExecutionStatus.RUNNING}:
        return WorkQueueBucket.IN_PROGRESS

    if status == DecisionStatus.IN_PROGRESS:
        return WorkQueueBucket.IN_PROGRESS

    if status == DecisionStatus.OPEN and _is_waiting_open(row, exec_status, last_action):
        return WorkQueueBucket.WAITING

    return WorkQueueBucket.TODO


def _is_waiting_open(row: Any, exec_status: str, last_action: str) -> bool:
    # Relance analyse réussie : le moteur traite, l’utilisateur attend
    if (
        last_action == DecisionActionType.RETRY_DOCUMENT_ANALYSIS
        and exec_status == DecisionExecutionStatus.SUCCEEDED
    ):
        return True
    # Échec d’exécution temporaire avec cause encore ouverte
    if exec_status == DecisionExecutionStatus.FAILED and getattr(
        row, "last_execution_error_code", None
    ) in {"business_error", "http_error", "internal_error"}:
        # Rester en todo pour permettre de réessayer — pas waiting
        return False
    return False


def waiting_reason_for(row: Any) -> dict[str, str] | None:
    if resolve_work_queue_bucket(row) != WorkQueueBucket.WAITING:
        return None
    last_action = getattr(row, "last_action_type", None) or ""
    if last_action == DecisionActionType.RETRY_DOCUMENT_ANALYSIS:
        return {
            "code": WaitingReasonCode.ANALYSIS_IN_PROGRESS,
            "label": "Analyse documentaire en cours",
            "description": "Une relance a été demandée. Le traitement système n’est pas encore terminé.",
        }
    exec_status = getattr(row, "execution_status", None)
    if exec_status == DecisionExecutionStatus.RUNNING:
        return {
            "code": WaitingReasonCode.EXECUTION_RUNNING,
            "label": "Traitement en cours",
            "description": "Une action a été lancée et attend sa confirmation.",
        }
    if exec_status == DecisionExecutionStatus.PENDING:
        return {
            "code": WaitingReasonCode.EXECUTION_PENDING,
            "label": "Action en file d’attente",
            "description": "Le traitement est planifié et n’a pas encore démarré.",
        }
    return {
        "code": WaitingReasonCode.ACTION_TEMPORARILY_UNAVAILABLE,
        "label": "En attente d’une mise à jour",
        "description": "La ressource source est en cours de traitement.",
    }
