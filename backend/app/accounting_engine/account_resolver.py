"""AccountResolver — résolution multi-sources (règles → config → historique → défauts)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.enums import AccountPlan, DocumentDirection
from app.accounting_engine.models import ElfisChartOfAccount
from app.config import settings
from app.models import CompanySettings


@dataclass
class ResolvedAccounts:
    expense_or_revenue: str
    vat_account: str
    third_party: str
    plan_code: str = AccountPlan.PCG_FR.value
    sources: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "expense_or_revenue": self.expense_or_revenue,
            "vat_account": self.vat_account,
            "third_party": self.third_party,
            "plan_code": self.plan_code,
            "sources": self.sources,
            "warnings": self.warnings,
        }


class AccountResolver:
    """
    Priorité :
    1. règles métier (rule hints)
    2. configuration entreprise (CompanySettings)
    3. historique (learning hints)
    4. similarité
    5. IA locale
    6. défauts ELFIS / plan comptable
    """

    def __init__(self, db: Session):
        self._db = db

    def resolve(
        self,
        *,
        organization_id: int,
        direction: str,
        document_type: str | None = None,
        rule_hints: dict[str, str] | None = None,
        learning_hints: dict[str, str] | None = None,
        similarity_hints: dict[str, str] | None = None,
        ai_hints: dict[str, str] | None = None,
        recommendation_hints: dict[str, str] | None = None,
        plan_code: str = AccountPlan.PCG_FR.value,
    ) -> ResolvedAccounts:
        rule_hints = rule_hints or {}
        learning_hints = learning_hints or {}
        similarity_hints = similarity_hints or {}
        ai_hints = ai_hints or {}
        recommendation_hints = recommendation_hints or {}
        sources: dict[str, str] = {}
        warnings: list[str] = []

        company = (
            self._db.query(CompanySettings)
            .filter(CompanySettings.organization_id == organization_id)
            .first()
        )

        is_sale = direction in {
            DocumentDirection.SALE.value,
            "sale",
            "vente",
        }

        # 0 Recommandation Intelligence déjà priorisée (si fournie)
        expense = recommendation_hints.get("expense_or_revenue")
        vat = recommendation_hints.get("vat_account")
        third = recommendation_hints.get("third_party")
        if expense:
            sources["expense_or_revenue"] = "recommendation"
        if vat:
            sources["vat_account"] = "recommendation"
        if third:
            sources["third_party"] = "recommendation"

        # 1 Règles
        if not expense and rule_hints.get("expense_or_revenue"):
            expense = rule_hints.get("expense_or_revenue")
            sources["expense_or_revenue"] = "rules"
        if not vat and rule_hints.get("vat_account"):
            vat = rule_hints.get("vat_account")
            sources["vat_account"] = "rules"
        if not third and rule_hints.get("third_party"):
            third = rule_hints.get("third_party")
            sources["third_party"] = "rules"

        # 2 Config entreprise
        if company:
            if not expense:
                expense = (
                    (company.expense_account if not is_sale else None)
                    or None
                )
                if is_sale:
                    # pas de revenue_account dédié → 707
                    expense = None
                elif company.expense_account:
                    expense = company.expense_account
                    sources["expense_or_revenue"] = "company_settings"
            if not vat and company.vat_account:
                vat = company.vat_account
                sources["vat_account"] = "company_settings"
            if not third and company.supplier_account and not is_sale:
                third = company.supplier_account
                sources["third_party"] = "company_settings"

        # 3 Historique / learning
        if not expense and learning_hints.get("expense_or_revenue"):
            expense = learning_hints["expense_or_revenue"]
            sources["expense_or_revenue"] = "history"
        if not expense and is_sale and learning_hints.get("revenue_account"):
            expense = learning_hints["revenue_account"]
            sources["expense_or_revenue"] = "history"
        if not vat and learning_hints.get("vat_account"):
            vat = learning_hints["vat_account"]
            sources["vat_account"] = "history"
        if not third and learning_hints.get("third_party"):
            third = learning_hints["third_party"]
            sources["third_party"] = "history"

        # 4 Similarité
        if not expense and similarity_hints.get("expense_or_revenue"):
            expense = similarity_hints["expense_or_revenue"]
            sources["expense_or_revenue"] = "similarity"
        if not vat and similarity_hints.get("vat_account"):
            vat = similarity_hints["vat_account"]
            sources["vat_account"] = "similarity"
        if not third and similarity_hints.get("third_party"):
            third = similarity_hints["third_party"]
            sources["third_party"] = "similarity"

        # 5 IA locale
        if not expense and ai_hints.get("expense_or_revenue"):
            expense = ai_hints["expense_or_revenue"]
            sources["expense_or_revenue"] = "ai"
        if not vat and ai_hints.get("vat_account"):
            vat = ai_hints["vat_account"]
            sources["vat_account"] = "ai"
        if not third and ai_hints.get("third_party"):
            third = ai_hints["third_party"]
            sources["third_party"] = "ai"

        # 6 Défauts config ELFIS + COA
        if not expense:
            if is_sale:
                expense = getattr(settings, "elfis_default_sales_account", None) or "707"
            else:
                expense = getattr(settings, "elfis_default_purchase_account", None) or "606"
            sources.setdefault("expense_or_revenue", "defaults")
        if not vat:
            if is_sale:
                vat = getattr(settings, "elfis_default_collected_vat_account", None) or "44571"
            else:
                vat = getattr(settings, "elfis_default_deductible_vat_account", None) or "44566"
            sources.setdefault("vat_account", "defaults")
        if not third:
            third = (
                getattr(settings, "elfis_default_customer_account", None) or "411"
                if is_sale
                else getattr(settings, "elfis_default_supplier_account", None) or "401"
            )
            sources.setdefault("third_party", "defaults")

        # Vérifier présence dans COA org si disponible
        for code, role in (
            (expense, "expense_or_revenue"),
            (vat, "vat_account"),
            (third, "third_party"),
        ):
            if not self._in_coa(organization_id, plan_code, code):
                # soft — seed implicite PCG
                warnings.append(f"compte_hors_plan:{role}:{code}")

        return ResolvedAccounts(
            expense_or_revenue=str(expense)[:16],
            vat_account=str(vat)[:16],
            third_party=str(third)[:16],
            plan_code=plan_code,
            sources=sources,
            warnings=warnings,
        )

    def _in_coa(self, organization_id: int, plan_code: str, account_code: str) -> bool:
        exists = (
            self._db.query(ElfisChartOfAccount.id)
            .filter(ElfisChartOfAccount.organization_id == organization_id)
            .filter(ElfisChartOfAccount.plan_code == plan_code)
            .filter(ElfisChartOfAccount.account_code == account_code)
            .filter(ElfisChartOfAccount.is_active.is_(True))
            .first()
        )
        if exists:
            return True
        # Si aucun COA chargé pour l'org → considérer PCG implicite OK
        any_coa = (
            self._db.query(ElfisChartOfAccount.id)
            .filter(ElfisChartOfAccount.organization_id == organization_id)
            .first()
        )
        return any_coa is None

    def ensure_default_pcg(self, organization_id: int) -> int:
        """Seed minimal PCG FR si plan vide."""
        count = (
            self._db.query(ElfisChartOfAccount)
            .filter(ElfisChartOfAccount.organization_id == organization_id)
            .count()
        )
        if count:
            return 0
        defaults = [
            ("401", "Fournisseurs", "third_party"),
            ("411", "Clients", "third_party"),
            ("44566", "TVA déductible", "vat"),
            ("44571", "TVA collectée", "vat"),
            ("512", "Banque", "bank"),
            ("530", "Caisse", "cash"),
            ("606", "Achats non stockés", "expense"),
            ("607", "Achats de marchandises", "expense"),
            ("625", "Déplacements, missions", "expense"),
            ("707", "Ventes de marchandises", "revenue"),
        ]
        for code, label, typ in defaults:
            self._db.add(
                ElfisChartOfAccount(
                    organization_id=organization_id,
                    plan_code=AccountPlan.PCG_FR.value,
                    account_code=code,
                    account_label=label,
                    account_type=typ,
                )
            )
        self._db.flush()
        return len(defaults)
