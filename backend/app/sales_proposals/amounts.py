"""Money helpers — Decimal only, round per line then sum."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.sales_proposals.enums import DiscountType

TWO = Decimal("0.01")
THREE = Decimal("0.001")


def money(value: Decimal | int | float | str | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(TWO, rounding=ROUND_HALF_UP)


def qty(value: Decimal | int | float | str | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(THREE, rounding=ROUND_HALF_UP)


def compute_line_amounts(
    *,
    quantity: Decimal | int | float | str,
    unit_price: Decimal | int | float | str,
    discount_type: str,
    discount_value: Decimal | int | float | str,
    tax_rate: Decimal | int | float | str,
) -> dict[str, Decimal]:
    """
    gross = qty × unit_price
    discount: none | percentage | fixed
    net_before_tax = gross − discount
    tax = net × tax_rate/100
    total = net + tax
    Round each monetary field to 2 decimals (currency), then sum at proposal level.
    """
    q = qty(quantity)
    price = money(unit_price)
    gross = money(q * price)
    dtype = (discount_type or DiscountType.none.value).lower()
    dval = money(discount_value)
    if dtype == DiscountType.percentage.value:
        discount_amount = money(gross * dval / Decimal("100"))
    elif dtype == DiscountType.fixed.value:
        discount_amount = min(dval, gross)
    else:
        discount_amount = money(0)
    net = money(gross - discount_amount)
    rate = money(tax_rate)
    tax_amount = money(net * rate / Decimal("100"))
    total = money(net + tax_amount)
    return {
        "subtotal": gross,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "total": total,
    }


def sum_totals(lines: list[dict[str, Decimal]]) -> dict[str, Decimal]:
    subtotal = money(sum((x["subtotal"] for x in lines), Decimal("0")))
    discount_total = money(sum((x["discount_amount"] for x in lines), Decimal("0")))
    tax_total = money(sum((x["tax_amount"] for x in lines), Decimal("0")))
    total = money(sum((x["total"] for x in lines), Decimal("0")))
    return {
        "subtotal": subtotal,
        "discount_total": discount_total,
        "tax_total": tax_total,
        "total": total,
    }
