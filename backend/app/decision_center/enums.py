"""Enums Decision Center — valeurs stables."""

from __future__ import annotations

from enum import StrEnum


class DecisionStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class DecisionSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionSourceType(StrEnum):
    ACCOUNTING_PROPOSAL = "accounting_proposal"
    DOCUMENT_ANALYSIS = "document_analysis"
    DOCUMENT_QUALITY = "document_quality"
    VAULT_DOCUMENT = "vault_document"
    JOB = "job"
    BILLING = "billing"
    NOTIFICATION = "notification"
    SYSTEM = "system"
    SALES_INSIGHT = "sales_insight"


class DecisionActionType(StrEnum):
    REVIEW = "review"
    VALIDATE = "validate"
    CORRECT = "correct"
    RETRY = "retry"
    COMPLETE_INFORMATION = "complete_information"
    OPEN_RESOURCE = "open_resource"
    CONTACT_SUPPORT = "contact_support"
    DISMISS = "dismiss"
    NO_ACTION = "no_action"
    # C1.16 — actions d’exécution explicites
    OPEN_ACCOUNTING_PROPOSAL = "open_accounting_proposal"
    OPEN_DOCUMENT = "open_document"
    VALIDATE_ACCOUNTING_PROPOSAL = "validate_accounting_proposal"
    RETRY_DOCUMENT_ANALYSIS = "retry_document_analysis"


class DecisionExecutionStatus(StrEnum):
    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DecisionExecutionAttemptStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DecisionEvidenceType(StrEnum):
    SOURCE_STATUS = "source_status"
    FINANCIAL_DIFFERENCE = "financial_difference"
    MISSING_FIELD = "missing_field"
    QUALITY_ISSUE = "quality_issue"
    FAILED_STEP = "failed_step"
    DETECTED_AMOUNT = "detected_amount"
    EXPECTED_AMOUNT = "expected_amount"
    DOCUMENT_REFERENCE = "document_reference"
    RULE_RESULT = "rule_result"
    REVIEW_REASON = "review_reason"


class DecisionType(StrEnum):
    ACCOUNTING_PROPOSAL_REQUIRES_REVIEW = "accounting_proposal_requires_review"
    ACCOUNTING_PROPOSAL_READY_FOR_VALIDATION = "accounting_proposal_ready_for_validation"
    DOCUMENT_ANALYSIS_FAILED = "document_analysis_failed"
    DOCUMENT_ANALYSIS_REQUIRES_REVIEW = "document_analysis_requires_review"
    SALES_INSIGHT_REQUIRES_ACTION = "sales_insight_requires_action"


SEVERITY_RANK = {
    DecisionSeverity.CRITICAL: 50,
    DecisionSeverity.HIGH: 40,
    DecisionSeverity.MEDIUM: 30,
    DecisionSeverity.LOW: 20,
    DecisionSeverity.INFO: 10,
}

# Types bloquants (priorisés après severity)
BLOCKING_TYPES = frozenset(
    {
        DecisionType.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW,
        DecisionType.ACCOUNTING_PROPOSAL_READY_FOR_VALIDATION,
        DecisionType.DOCUMENT_ANALYSIS_FAILED,
    }
)
