"""ConsistencyEngine — contrôles débit/crédit, TVA, montants, dates, devise."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.accounting.accounting_security import balance_tolerance


def _d(v: Any) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    return Decimal(str(v).replace(",", ".").replace(" ", ""))


@dataclass
class ConsistencyResult:
    balanced: bool
    ok: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_debit: float = 0.0
    total_credit: float = 0.0
    checks: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "balanced": self.balanced,
            "ok": self.ok,
            "warnings": self.warnings,
            "errors": self.errors,
            "total_debit": self.total_debit,
            "total_credit": self.total_credit,
            "checks": self.checks,
        }


class ConsistencyEngine:
    def check(
        self,
        *,
        lines: list[dict[str, Any]],
        amount_ht: Any = None,
        amount_vat: Any = None,
        amount_ttc: Any = None,
        currency: str | None = "EUR",
        document_date: str | None = None,
        accounts: list[str] | None = None,
    ) -> ConsistencyResult:
        warnings: list[str] = []
        errors: list[str] = []
        checks: dict[str, bool] = {}

        total_d = Decimal("0")
        total_c = Decimal("0")
        for line in lines:
            total_d += _d(line.get("debit"))
            total_c += _d(line.get("credit"))
            code = str(line.get("account_code") or line.get("account") or "")
            if not code:
                errors.append("compte_manquant")
            if _d(line.get("debit")) > 0 and _d(line.get("credit")) > 0:
                errors.append("ligne_debit_et_credit")

        tol = balance_tolerance() if callable(balance_tolerance) else Decimal("0.02")
        try:
            tol = Decimal(str(tol))
        except Exception:
            tol = Decimal("0.02")

        balanced = abs(total_d - total_c) <= tol
        checks["debit_credit"] = balanced
        if not balanced:
            errors.append("debit_credit_desequilibre")

        # Montants vs lignes
        ttc = _d(amount_ttc)
        if ttc > 0:
            # max(debit, credit) devrait ≈ TTC pour facture simple
            side = max(total_d, total_c)
            if abs(side - ttc) > tol:
                warnings.append("montant_ttc_vs_lignes")
            else:
                checks["amounts"] = True
        else:
            checks["amounts"] = True

        ht = _d(amount_ht)
        vat = _d(amount_vat)
        if ht and vat and ttc:
            if abs((ht + vat) - ttc) > tol:
                errors.append("tva_incoherente")
                checks["vat"] = False
            else:
                checks["vat"] = True
        else:
            checks["vat"] = True

        cur = (currency or "EUR").upper()
        checks["currency"] = len(cur) == 3
        if not checks["currency"]:
            warnings.append("devise_invalide")

        checks["date"] = True
        if document_date:
            try:
                # accept ISO or JJ-MM-AAAA
                if "-" in document_date and len(document_date) >= 8:
                    checks["date"] = True
                else:
                    warnings.append("date_format_douteux")
            except Exception:
                warnings.append("date_invalide")
                checks["date"] = False

        if accounts:
            for a in accounts:
                if not a:
                    errors.append("compte_vide")
                    checks["accounts"] = False
                    break
            else:
                checks["accounts"] = True
        else:
            checks["accounts"] = all(
                bool(l.get("account_code") or l.get("account")) for l in lines
            ) if lines else False

        ok = balanced and not errors
        return ConsistencyResult(
            balanced=balanced,
            ok=ok,
            warnings=warnings,
            errors=errors,
            total_debit=float(total_d),
            total_credit=float(total_c),
            checks=checks,
        )
