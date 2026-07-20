"""Types et constantes — ELFIS AI Engine."""

from __future__ import annotations


class AITaskNames:
    DOCUMENT_CLASSIFY = "document.classify.v1"
    DOCUMENT_EXTRACT_INVOICE = "document.extract_invoice.v1"
    DOCUMENT_QUALITY_CHECK = "document.quality_check.v1"

    # Préparés — non exécutés en V1
    DOCUMENT_EXTRACT_QUOTE = "document.extract_quote.v1"
    DOCUMENT_EXTRACT_CREDIT_NOTE = "document.extract_credit_note.v1"
    DOCUMENT_EXTRACT_BANK_STATEMENT = "document.extract_bank_statement.v1"
    DOCUMENT_ACCOUNTING_MAPPING = "document.accounting_mapping.v1"
    DOCUMENT_DETECT_DUPLICATES = "document.detect_duplicates.v1"
    ASSISTANT_CHAT = "assistant.chat.v1"
    SALES_LEAD_SCORE = "sales.lead_score.v1"
    LEGAL_CONTRACT_REVIEW = "legal.contract_review.v1"


IMPLEMENTED_AI_TASKS: frozenset[str] = frozenset(
    {
        AITaskNames.DOCUMENT_CLASSIFY,
        AITaskNames.DOCUMENT_EXTRACT_INVOICE,
        AITaskNames.DOCUMENT_QUALITY_CHECK,
    }
)

ALL_KNOWN_AI_TASKS: frozenset[str] = frozenset(
    getattr(AITaskNames, name)
    for name in dir(AITaskNames)
    if name.isupper() and not name.startswith("_")
)


class AIProviders:
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    GOOGLE_GEMINI = "google_gemini"
    LOCAL = "local"


IMPLEMENTED_PROVIDERS: frozenset[str] = frozenset({AIProviders.OPENAI})


class AIExecutionStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    REQUIRES_REVIEW = "requires_review"


class DocumentAnalysisStatus:
    PENDING = "pending"
    CLASSIFYING = "classifying"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"
    BLOCKED = "blocked"


CLASSIFICATION_TYPES: frozenset[str] = frozenset(
    {
        "customer_invoice",
        "supplier_invoice",
        "quote",
        "credit_note",
        "expense_report",
        "bank_statement",
        "contract",
        "receipt",
        "other",
    }
)

# Mapping heuristique Document Reader (FR) → types Vault/AI
READER_TYPE_TO_AI: dict[str, str] = {
    "facture": "supplier_invoice",
    "avoir": "credit_note",
    "devis": "quote",
    "ticket": "receipt",
    "note_frais": "expense_report",
    "releve": "bank_statement",
    "autre": "other",
}
