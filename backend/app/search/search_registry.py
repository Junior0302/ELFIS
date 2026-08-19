"""Registry des indexers Search."""

from __future__ import annotations

from app.search.indexers.accounting_indexer import (
    AccountingEntryIndexer,
    AccountingProposalIndexer,
)
from app.search.indexers.base import ResourceIndexer
from app.search.indexers.contact_indexer import CustomerIndexer, SupplierIndexer
from app.search.indexers.document_analysis_indexer import (
    DocumentAnalysisIndexer,
    DocumentTextExtractionIndexer,
)
from app.search.indexers.vault_document_indexer import VaultDocumentIndexer
from app.search.search_exceptions import SearchValidationError
from app.sales_crm.search_indexers import (
    SalesActivityIndexer,
    SalesCompanyIndexer,
    SalesLeadIndexer,
    SalesOpportunityIndexer,
    SalesPersonIndexer,
    SalesTaskIndexer,
)
from app.sales_proposals.search_indexer import SalesProposalIndexer


class SearchIndexerRegistry:
    def __init__(self) -> None:
        self._by_type: dict[str, ResourceIndexer] = {}

    def register(self, indexer: ResourceIndexer) -> None:
        rtype = (indexer.resource_type or "").strip()
        if not rtype:
            raise SearchValidationError("resource_type indexer requis")
        if rtype in self._by_type and self._by_type[rtype] is not indexer:
            raise SearchValidationError(f"Indexer déjà enregistré: {rtype}")
        self._by_type[rtype] = indexer

    def get(self, resource_type: str) -> ResourceIndexer:
        if resource_type not in self._by_type:
            raise SearchValidationError(f"Type de ressource inconnu: {resource_type}")
        return self._by_type[resource_type]

    def has(self, resource_type: str) -> bool:
        return resource_type in self._by_type

    def clear(self) -> None:
        self._by_type.clear()


default_indexer_registry = SearchIndexerRegistry()


def bootstrap_indexers(registry: SearchIndexerRegistry | None = None) -> SearchIndexerRegistry:
    reg = registry or default_indexer_registry
    if not reg._by_type:
        for indexer in (
            VaultDocumentIndexer(),
            DocumentTextExtractionIndexer(),
            DocumentAnalysisIndexer(),
            AccountingProposalIndexer(),
            AccountingEntryIndexer(),
            CustomerIndexer(),
            SupplierIndexer(),
            SalesLeadIndexer(),
            SalesCompanyIndexer(),
            SalesPersonIndexer(),
            SalesOpportunityIndexer(),
            SalesTaskIndexer(),
            SalesActivityIndexer(),
            SalesProposalIndexer(),
        ):
            reg.register(indexer)
    return reg
