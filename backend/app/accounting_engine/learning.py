"""LearningEngine — mémorise validations utilisateur (sans modifier règles globales)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.enums import LearningSource
from app.accounting_engine.models import ElfisAccountingLearningMemory


def memory_key(
    *,
    direction: str,
    document_type: str,
    party_name: str | None,
) -> str:
    raw = f"{direction}|{document_type}|{(party_name or '').strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


class LearningEngine:
    def __init__(self, db: Session):
        self._db = db

    def lookup(
        self,
        *,
        organization_id: int,
        direction: str,
        document_type: str,
        party_name: str | None,
    ) -> dict[str, str]:
        key = memory_key(
            direction=direction, document_type=document_type, party_name=party_name
        )
        row = (
            self._db.query(ElfisAccountingLearningMemory)
            .filter(ElfisAccountingLearningMemory.organization_id == organization_id)
            .filter(ElfisAccountingLearningMemory.memory_key == key)
            .first()
        )
        if not row:
            return {}
        row.hit_count = int(row.hit_count or 0) + 1
        row.last_used_at = datetime.utcnow()
        self._db.add(row)
        self._db.flush()
        hints: dict[str, str] = {}
        if row.preferred_expense_account:
            hints["expense_or_revenue"] = row.preferred_expense_account
        if row.preferred_revenue_account:
            hints["revenue_account"] = row.preferred_revenue_account
        if row.preferred_vat_account:
            hints["vat_account"] = row.preferred_vat_account
        if row.preferred_third_party_account:
            hints["third_party"] = row.preferred_third_party_account
        if row.preferred_journal:
            hints["journal"] = row.preferred_journal
        return hints

    def remember(
        self,
        *,
        organization_id: int,
        direction: str,
        document_type: str,
        party_name: str | None,
        accounts: dict[str, str],
        journal: str | None = None,
        vat_rate: float | None = None,
        actor_user_id: int | None = None,
        source: str = LearningSource.USER_VALIDATION.value,
    ) -> ElfisAccountingLearningMemory:
        key = memory_key(
            direction=direction, document_type=document_type, party_name=party_name
        )
        row = (
            self._db.query(ElfisAccountingLearningMemory)
            .filter(ElfisAccountingLearningMemory.organization_id == organization_id)
            .filter(ElfisAccountingLearningMemory.memory_key == key)
            .first()
        )
        if not row:
            row = ElfisAccountingLearningMemory(
                organization_id=organization_id,
                memory_key=key,
                supplier_or_customer=party_name,
                document_type=document_type,
                direction=direction,
            )
        row.preferred_expense_account = accounts.get("expense_or_revenue") or row.preferred_expense_account
        row.preferred_revenue_account = accounts.get("revenue_account") or row.preferred_revenue_account
        row.preferred_vat_account = accounts.get("vat_account") or row.preferred_vat_account
        row.preferred_third_party_account = accounts.get("third_party") or row.preferred_third_party_account
        if journal:
            row.preferred_journal = journal
        if vat_rate is not None:
            row.vat_rate = vat_rate
        row.source = source
        row.hit_count = int(row.hit_count or 0) + 1
        row.last_used_at = datetime.utcnow()
        row.payload_json = {
            "accounts": accounts,
            "journal": journal,
            "actor_user_id": actor_user_id,
        }
        self._db.add(row)
        self._db.flush()
        return row
