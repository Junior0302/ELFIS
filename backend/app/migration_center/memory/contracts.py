"""Contrats Migration Memory — pas de règles comptables métier."""

from __future__ import annotations

from typing import Protocol


class MigrationMemoryContract(Protocol):
    """Interface future pour apprentissage / réutilisation de décisions."""

    def propose(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        memory_type: str,
        key_hash: str,
        payload: dict,
        scope: str = "session",
    ) -> object: ...

    def list_for_session(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
    ) -> list: ...
