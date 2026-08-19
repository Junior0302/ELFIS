"""Service Migration Memory — écriture limitée à scope=session."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.migration_center.exceptions import MigrationAccessDeniedError, MigrationValidationError
from app.migration_center.memory.enums import WRITABLE_SCOPES, MemoryScope
from app.migration_center.memory.repository import MigrationMemoryRepository
from app.migration_center.models import ElfisMigrationMemoryEntry

logger = logging.getLogger(__name__)

# Clés interdites — pas de règles comptables métier dans ELFIS Core
_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "ledger_entry",
        "journal_entry",
        "account_number",
        "iban",
        "bank_account",
        "tax_rate_rule",
        "compta_rule",
    }
)


class MigrationMemoryService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = MigrationMemoryRepository(db)

    def _assert_writable_scope(self, scope: str) -> None:
        if scope not in WRITABLE_SCOPES:
            raise MigrationValidationError(
                "memory_scope_forbidden",
                "Seul le scope session est autorisé en écriture pour cette version.",
            )
        if scope == MemoryScope.PRODUCT.value:
            raise MigrationValidationError(
                "memory_global_forbidden",
                "Mémoire globale inter-organisations interdite.",
            )

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        clean = dict(payload or {})
        for k in list(clean.keys()):
            if k.lower() in _FORBIDDEN_PAYLOAD_KEYS:
                raise MigrationValidationError(
                    "memory_accounting_forbidden",
                    "Les règles comptables métier ne peuvent pas être stockées dans Migration Memory.",
                )
        return clean

    def propose(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        memory_type: str,
        key_hash: str,
        payload: dict[str, Any],
        scope: str = MemoryScope.SESSION.value,
        source: str = "system",
        confidence: float | None = None,
        created_by_user_id: int | None = None,
        commit: bool = True,
    ) -> ElfisMigrationMemoryEntry:
        self._assert_writable_scope(scope)
        clean = self._sanitize_payload(payload)
        return self._repo.create(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            scope=scope,
            memory_type=memory_type,
            key_hash=key_hash,
            payload=clean,
            source=source,
            status="proposed",
            confidence=confidence,
            created_by_user_id=created_by_user_id,
            commit=commit,
        )

    def list_for_session(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        limit: int = 100,
    ) -> list[ElfisMigrationMemoryEntry]:
        return self._repo.list_for_session(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            limit=limit,
        )

    def get_for_org(self, entry_id: str, organization_id: int) -> ElfisMigrationMemoryEntry:
        row = self._repo.get_for_org(entry_id, organization_id)
        if not row:
            raise MigrationAccessDeniedError("memory_not_found", "Entrée mémoire introuvable")
        return row
