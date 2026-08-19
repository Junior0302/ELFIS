"""indexers package."""

from app.search.indexers.accounting_indexer import AccountingEntryIndexer, AccountingProposalIndexer
from app.search.indexers.contact_indexer import CustomerIndexer, SupplierIndexer
from app.search.indexers.document_analysis_indexer import (
    DocumentAnalysisIndexer,
    DocumentTextExtractionIndexer,
)
from app.search.indexers.vault_document_indexer import VaultDocumentIndexer

__all__ = [
    "VaultDocumentIndexer",
    "DocumentAnalysisIndexer",
    "DocumentTextExtractionIndexer",
    "AccountingProposalIndexer",
    "AccountingEntryIndexer",
    "CustomerIndexer",
    "SupplierIndexer",
]
