"""Construction des available_actions V2 (déterministe)."""

from __future__ import annotations

from typing import Any, Callable

from app.decision_center.enums import (
    DecisionActionType,
    DecisionStatus,
    DecisionType,
)
from app.decision_center.schemas import DecisionActionOut


AllowsFn = Callable[[list[str], str], bool]


def build_available_actions(
    *,
    row: Any,
    permissions: list[str],
    allows: AllowsFn,
    source: Any | None,
) -> list[DecisionActionOut]:
    if row.status not in {DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS}:
        return []

    actions: list[DecisionActionOut] = []
    dt = row.decision_type

    if dt in {
        DecisionType.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW,
        DecisionType.ACCOUNTING_PROPOSAL_READY_FOR_VALIDATION,
    }:
        actions.extend(_accounting_actions(row, permissions, allows, source))
    elif dt in {
        DecisionType.DOCUMENT_ANALYSIS_FAILED,
        DecisionType.DOCUMENT_ANALYSIS_REQUIRES_REVIEW,
    }:
        actions.extend(_document_actions(row, permissions, allows, source))

    # Dismiss disponible tant que non résolue/ignorée
    if row.status in {DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS}:
        actions.append(
            DecisionActionOut(
                action_type=DecisionActionType.DISMISS,
                label="Ignorer",
                description="Masque cette décision sans corriger la cause métier.",
                method="POST",
                endpoint=f"/api/decisions/{row.id}/dismiss",
                requires_confirmation=row.severity in {"high", "critical"},
                destructive=False,
                enabled=True,
                idempotency_supported=False,
                expected_resolution_behavior="dismiss_only",
            )
        )
    return actions


def _accounting_actions(
    row: Any, permissions: list[str], allows: AllowsFn, source: Any | None
) -> list[DecisionActionOut]:
    proposal_id = row.source_id
    path = f"/accounting/proposals/{proposal_id}"
    can_view = allows(permissions, "ai.analysis") or allows(permissions, "documents.read")
    can_validate = allows(permissions, "accounting.validate") or allows(
        permissions, "ai.analysis"
    ) or allows(permissions, "documents.write")

    source_ok = source is not None
    status = getattr(source, "status", None) if source else None
    validable = status in {"ready_for_validation", "requires_review"} if source_ok else False

    open_enabled = can_view and source_ok
    actions = [
        DecisionActionOut(
            action_type=DecisionActionType.OPEN_ACCOUNTING_PROPOSAL,
            label="Examiner la proposition",
            description="Ouvre la proposition comptable pour comprendre et corriger.",
            method="NAVIGATE",
            action_path=path if open_enabled else None,
            opens_source=True,
            required_permission="ai.analysis",
            enabled=open_enabled,
            disabled_reason=None
            if open_enabled
            else (
                "La proposition associée n’est plus disponible."
                if not source_ok
                else "Permission insuffisante pour consulter la proposition."
            ),
            expected_resolution_behavior="resolve_when_proposal_validated_or_rejected",
        )
    ]

    validate_enabled = can_validate and validable and row.status in {
        DecisionStatus.OPEN,
        DecisionStatus.IN_PROGRESS,
    }
    disabled_reason = None
    if not source_ok:
        disabled_reason = "La proposition associée n’est plus disponible."
    elif not can_validate:
        disabled_reason = "Permission insuffisante pour valider."
    elif not validable:
        disabled_reason = "La proposition n’est plus validable dans son état actuel."
    elif getattr(row, "execution_status", None) == "running":
        disabled_reason = "Une action est déjà en cours sur cette décision."
        validate_enabled = False

    actions.append(
        DecisionActionOut(
            action_type=DecisionActionType.VALIDATE_ACCOUNTING_PROPOSAL,
            label="Valider la proposition",
            description="Confirme l’écriture via le module Accounting (confirmations requises).",
            method="POST",
            endpoint=f"/api/decisions/{row.id}/actions/{DecisionActionType.VALIDATE_ACCOUNTING_PROPOSAL}",
            action_path=path,
            requires_confirmation=True,
            destructive=False,
            required_permission="accounting.validate",
            enabled=validate_enabled,
            disabled_reason=disabled_reason if not validate_enabled else None,
            idempotency_supported=True,
            opens_source=False,
            expected_resolution_behavior="resolve_when_proposal_validated",
        )
    )
    return actions


def _document_actions(
    row: Any, permissions: list[str], allows: AllowsFn, source: Any | None
) -> list[DecisionActionOut]:
    vault_id = None
    if source is not None:
        vault_id = getattr(source, "vault_document_id", None)
    if not vault_id and isinstance(getattr(row, "metadata_json", None), dict):
        vault_id = row.metadata_json.get("vault_document_id")

    path = f"/documents?document_id={vault_id}" if vault_id else "/documents"
    can_view = allows(permissions, "documents.read") or allows(permissions, "ai.analysis")
    can_retry = allows(permissions, "documents.write") or allows(permissions, "ai.analysis")
    source_ok = source is not None
    status = getattr(source, "status", None) if source else None
    retryable = status == "failed" and bool(vault_id)

    open_enabled = can_view
    actions = [
        DecisionActionOut(
            action_type=DecisionActionType.OPEN_DOCUMENT,
            label="Examiner le document",
            description="Ouvre l’espace documentaire sur le document concerné.",
            method="NAVIGATE",
            action_path=path if open_enabled else None,
            opens_source=True,
            required_permission="documents.read",
            enabled=open_enabled,
            disabled_reason=None
            if open_enabled
            else "Permission insuffisante pour consulter les documents.",
            expected_resolution_behavior="resolve_when_analysis_succeeds",
        )
    ]

    if row.decision_type == DecisionType.DOCUMENT_ANALYSIS_FAILED:
        retry_enabled = can_retry and retryable and getattr(row, "execution_status", None) != "running"
        disabled_reason = None
        if not source_ok:
            disabled_reason = "L’analyse associée n’est plus disponible."
        elif not can_retry:
            disabled_reason = "Permission insuffisante pour relancer l’analyse."
        elif status != "failed":
            disabled_reason = "L’analyse n’est plus en échec."
        elif not vault_id:
            disabled_reason = "Référence document manquante — relance impossible."
        elif getattr(row, "execution_status", None) == "running":
            disabled_reason = "Une relance est déjà en cours."

        actions.append(
            DecisionActionOut(
                action_type=DecisionActionType.RETRY_DOCUMENT_ANALYSIS,
                label="Relancer l’analyse",
                description="Relance le traitement via le service d’analyse documentaire existant.",
                method="POST",
                endpoint=f"/api/decisions/{row.id}/actions/{DecisionActionType.RETRY_DOCUMENT_ANALYSIS}",
                action_path=path,
                requires_confirmation=True,
                destructive=False,
                required_permission="ai.analysis",
                enabled=retry_enabled,
                disabled_reason=disabled_reason if not retry_enabled else None,
                idempotency_supported=True,
                expected_resolution_behavior="resolve_when_analysis_succeeds",
            )
        )
    return actions
