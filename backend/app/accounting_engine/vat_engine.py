"""VATEngine — calcul et contrôles TVA."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.accounting_engine.enums import STANDARD_VAT_RATES


def _d(v: Any) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    return Decimal(str(v).replace(",", ".").replace(" ", ""))


def _money(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class VatResult:
    amount_ht: Decimal
    amount_vat: Decimal
    amount_ttc: Decimal
    vat_rate: Decimal | None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rounded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount_ht": float(self.amount_ht),
            "amount_vat": float(self.amount_vat),
            "amount_ttc": float(self.amount_ttc),
            "vat_rate": float(self.vat_rate) if self.vat_rate is not None else None,
            "warnings": self.warnings,
            "errors": self.errors,
            "rounded": self.rounded,
        }


class VATEngine:
    TOLERANCE = Decimal("0.02")

    def compute(
        self,
        *,
        amount_ht: Any = None,
        amount_vat: Any = None,
        amount_ttc: Any = None,
        vat_rate: Any = None,
        exempt: bool = False,
    ) -> VatResult:
        ht = _d(amount_ht)
        vat = _d(amount_vat)
        ttc = _d(amount_ttc)
        rate = _d(vat_rate) if vat_rate is not None and str(vat_rate) != "" else None
        warnings: list[str] = []
        errors: list[str] = []
        rounded = False

        if exempt:
            return VatResult(
                amount_ht=_money(ht or ttc),
                amount_vat=Decimal("0.00"),
                amount_ttc=_money(ht or ttc),
                vat_rate=Decimal("0"),
                warnings=["tva_exoneree"],
            )

        # Compléter les montants manquants
        if rate is not None and rate > 0:
            if ht and not ttc:
                vat = _money(ht * rate / Decimal("100"))
                ttc = _money(ht + vat)
                rounded = True
            elif ttc and not ht:
                ht = _money(ttc / (Decimal("1") + rate / Decimal("100")))
                vat = _money(ttc - ht)
                rounded = True
            elif ht and not vat:
                vat = _money(ht * rate / Decimal("100"))
                if not ttc:
                    ttc = _money(ht + vat)
                rounded = True

        if not ht and not ttc and not vat:
            errors.append("montants_absents")
            return VatResult(
                amount_ht=Decimal("0"),
                amount_vat=Decimal("0"),
                amount_ttc=Decimal("0"),
                vat_rate=rate,
                errors=errors,
            )

        if ht and vat and not ttc:
            ttc = _money(ht + vat)
            rounded = True
        if ttc and ht and not vat:
            vat = _money(ttc - ht)
            rounded = True
        if ttc and vat and not ht:
            ht = _money(ttc - vat)
            rounded = True

        ht, vat, ttc = _money(ht), _money(vat), _money(ttc)

        # Cohérence HT + TVA ≈ TTC
        if abs((ht + vat) - ttc) > self.TOLERANCE:
            errors.append("tva_impossible_ecart_ttc")
        elif abs((ht + vat) - ttc) > Decimal("0") and abs((ht + vat) - ttc) <= self.TOLERANCE:
            warnings.append("arrondi_tva")
            rounded = True

        # Taux incohérent
        if ht > 0 and vat >= 0:
            implied = (vat / ht * Decimal("100")).quantize(Decimal("0.1"))
            if rate is not None:
                if abs(implied - rate) > Decimal("0.5"):
                    warnings.append("taux_incoherent")
            else:
                rate = implied
                closest = min(
                    (Decimal(str(r)) for r in STANDARD_VAT_RATES),
                    key=lambda r: abs(r - implied),
                )
                if abs(closest - implied) <= Decimal("0.6"):
                    rate = closest
                else:
                    warnings.append("taux_non_standard")

        if vat == 0 and ht > 0 and (rate is None or rate == 0):
            warnings.append("tva_absente")

        if rate is not None and float(rate) not in STANDARD_VAT_RATES and rate != 0:
            if abs(rate - Decimal("20")) > Decimal("0.01"):
                warnings.append("taux_hors_bareme_fr")

        return VatResult(
            amount_ht=ht,
            amount_vat=vat,
            amount_ttc=ttc,
            vat_rate=rate,
            warnings=warnings,
            errors=errors,
            rounded=rounded,
        )
