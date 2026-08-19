"""Interface indexer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from app.search.search_schemas import BuiltSearchDocument


class ResourceIndexer(ABC):
    resource_type: str

    @abstractmethod
    def supports(self, resource_type: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def load_resource(self, db: Session, *, organization_id: int, resource_id: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def build_search_document(
        self,
        resource: Any,
        *,
        organization_id: int,
        resource_version: int = 1,
        **kwargs: Any,
    ) -> BuiltSearchDocument:
        raise NotImplementedError
