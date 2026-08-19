"""ContextEngine — profil entreprise isolé par tenant."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.models import ElfisAccountingEngineProposal
from app.accounting_intelligence.models import (
    ElfisAiContextProfile,
    ElfisAiFeedback,
    ElfisAiLearningMemory,
    ElfisAiRecommendationHistory,
)
from app.models import CompanySettings


class ContextEngine:
    def __init__(self, db: Session):
        self._db = db

    def get_or_create(self, *, organization_id: int) -> ElfisAiContextProfile:
        row = (
            self._db.query(ElfisAiContextProfile)
            .filter(ElfisAiContextProfile.organization_id == organization_id)
            .first()
        )
        if row:
            return row
        row = ElfisAiContextProfile(organization_id=organization_id)
        self._db.add(row)
        self._db.flush()
        return row

    def profile_dict(self, *, organization_id: int) -> dict[str, Any]:
        row = self.get_or_create(organization_id=organization_id)
        return {
            "organization_id": organization_id,
            "frequent_accounts": row.frequent_accounts_json or [],
            "favorite_journals": row.favorite_journals_json or [],
            "habitual_vat_rates": row.habitual_vat_rates_json or [],
            "exceptions": row.exceptions_json or [],
            "preferences": row.preferences_json or {},
            "stats": row.stats_json or {},
            "version": row.version,
            "rebuilt_at": row.rebuilt_at.isoformat() if row.rebuilt_at else None,
        }

    def company_preferences(self, *, organization_id: int) -> dict[str, str]:
        company = (
            self._db.query(CompanySettings)
            .filter(CompanySettings.organization_id == organization_id)
            .first()
        )
        if not company:
            return {}
        prefs: dict[str, str] = {}
        if company.expense_account:
            prefs["expense_or_revenue"] = company.expense_account
        if company.vat_account:
            prefs["vat_account"] = company.vat_account
        if company.supplier_account:
            prefs["third_party"] = company.supplier_account
        return prefs

    def rebuild(self, *, organization_id: int) -> ElfisAiContextProfile:
        """Reconstruit le profil depuis historique local (tenant only)."""
        row = self.get_or_create(organization_id=organization_id)

        accounts: Counter[str] = Counter()
        journals: Counter[str] = Counter()
        vat_rates: Counter[str] = Counter()
        exceptions: list[dict[str, Any]] = []

        for mem in (
            self._db.query(ElfisAiLearningMemory)
            .filter(ElfisAiLearningMemory.organization_id == organization_id)
            .filter(ElfisAiLearningMemory.is_current.is_(True))
            .all()
        ):
            for code in (mem.preferred_accounts_json or {}).values():
                if code:
                    accounts[str(code)] += 1
            if mem.preferred_journal:
                journals[mem.preferred_journal] += 1
            if mem.vat_rate is not None:
                vat_rates[str(mem.vat_rate)] += 1

        for rec in (
            self._db.query(ElfisAiRecommendationHistory)
            .filter(ElfisAiRecommendationHistory.organization_id == organization_id)
            .order_by(ElfisAiRecommendationHistory.created_at.desc())
            .limit(200)
            .all()
        ):
            if rec.account_code:
                accounts[rec.account_code] += 1
            if rec.journal_code:
                journals[rec.journal_code] += 1
            if rec.vat_rate is not None:
                vat_rates[str(rec.vat_rate)] += 1

        for prop in (
            self._db.query(ElfisAccountingEngineProposal)
            .filter(ElfisAccountingEngineProposal.organization_id == organization_id)
            .order_by(ElfisAccountingEngineProposal.created_at.desc())
            .limit(100)
            .all()
        ):
            if prop.journal_code:
                journals[prop.journal_code] += 1
            if prop.vat_rate is not None:
                vat_rates[str(prop.vat_rate)] += 1
            for line in prop.lines_json or []:
                code = line.get("account_code")
                if code:
                    accounts[str(code)] += 1
            if prop.warnings_json:
                exceptions.append(
                    {
                        "proposal_id": prop.id,
                        "warnings": list(prop.warnings_json)[:5],
                    }
                )

        fb_count = (
            self._db.query(ElfisAiFeedback)
            .filter(ElfisAiFeedback.organization_id == organization_id)
            .count()
        )
        accepted = (
            self._db.query(ElfisAiFeedback)
            .filter(ElfisAiFeedback.organization_id == organization_id)
            .filter(ElfisAiFeedback.action == "accept")
            .count()
        )

        prefs = self.company_preferences(organization_id=organization_id)
        row.frequent_accounts_json = [
            {"account_code": c, "count": n} for c, n in accounts.most_common(20)
        ]
        row.favorite_journals_json = [
            {"journal_code": j, "count": n} for j, n in journals.most_common(10)
        ]
        row.habitual_vat_rates_json = [
            {"vat_rate": float(r), "count": n} for r, n in vat_rates.most_common(5)
        ]
        row.exceptions_json = exceptions[:20]
        row.preferences_json = prefs
        row.stats_json = {
            "feedback_count": fb_count,
            "accepted_count": accepted,
            "accept_rate": (accepted / fb_count) if fb_count else None,
            "proposals_sampled": min(100, sum(accounts.values()) if accounts else 0),
        }
        row.version = int(row.version or 0) + 1
        row.rebuilt_at = datetime.utcnow()
        self._db.add(row)
        self._db.flush()
        return row
