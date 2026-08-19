"""ELFIS Search Engine V1."""

from app.search.search_registry import bootstrap_indexers
from app.search.search_service import SearchService

__all__ = ["SearchService", "bootstrap_indexers"]
