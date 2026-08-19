"""Types Search Engine."""

from __future__ import annotations


class SearchResourceTypes:
    VAULT_DOCUMENT = "vault_document"
    DOCUMENT_TEXT_EXTRACTION = "document_text_extraction"
    DOCUMENT_ANALYSIS = "document_analysis"
    ACCOUNTING_PROPOSAL = "accounting_proposal"
    ACCOUNTING_ENTRY = "accounting_entry"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    SALES_LEAD = "sales_lead"
    SALES_COMPANY = "sales_company"
    SALES_PERSON = "sales_person"
    SALES_OPPORTUNITY = "sales_opportunity"
    SALES_TASK = "sales_task"
    SALES_ACTIVITY = "sales_activity"
    SALES_PROPOSAL = "sales_proposal"

    # Préparés — non indexés automatiquement en V1
    EMAIL = "email"
    BANK_TRANSACTION = "bank_transaction"
    SUBSCRIPTION = "subscription"
    AUDIT_LOG = "audit_log"
    KNOWLEDGE_BASE = "knowledge_base"


INDEXED_RESOURCE_TYPES_V1: frozenset[str] = frozenset(
    {
        SearchResourceTypes.VAULT_DOCUMENT,
        SearchResourceTypes.DOCUMENT_TEXT_EXTRACTION,
        SearchResourceTypes.DOCUMENT_ANALYSIS,
        SearchResourceTypes.ACCOUNTING_PROPOSAL,
        SearchResourceTypes.ACCOUNTING_ENTRY,
        SearchResourceTypes.CUSTOMER,
        SearchResourceTypes.SUPPLIER,
        SearchResourceTypes.SALES_LEAD,
        SearchResourceTypes.SALES_COMPANY,
        SearchResourceTypes.SALES_PERSON,
        SearchResourceTypes.SALES_OPPORTUNITY,
        SearchResourceTypes.SALES_TASK,
        SearchResourceTypes.SALES_ACTIVITY,
        SearchResourceTypes.SALES_PROPOSAL,
    }
)

PREPARED_RESOURCE_TYPES: frozenset[str] = frozenset(
    {
        SearchResourceTypes.EMAIL,
        SearchResourceTypes.BANK_TRANSACTION,
        SearchResourceTypes.SUBSCRIPTION,
        SearchResourceTypes.AUDIT_LOG,
        SearchResourceTypes.KNOWLEDGE_BASE,
    }
)


class SearchCategories:
    DOCUMENT = "document"
    ANALYSIS = "analysis"
    ACCOUNTING = "accounting"
    CONTACT = "contact"
    SALES = "sales"


class SearchSort:
    RELEVANCE = "relevance"
    NEWEST = "newest"
    OLDEST = "oldest"
    AMOUNT_HIGH = "amount_high"
    AMOUNT_LOW = "amount_low"


SUPPORTED_SORTS: frozenset[str] = frozenset(
    {
        SearchSort.RELEVANCE,
        SearchSort.NEWEST,
        SearchSort.OLDEST,
        SearchSort.AMOUNT_HIGH,
        SearchSort.AMOUNT_LOW,
    }
)


class IndexStatus:
    INDEXED = "indexed"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    REMOVED = "removed"
    FAILED = "failed"
