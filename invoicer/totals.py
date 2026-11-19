"""The totals of lines for library callers, from each line's exact amount; the colleague's
printed invoice adds its amounts rounded to the cent, which page.py decides."""

from __future__ import annotations

from decimal import Decimal

from invoicer.lines import Line
from invoicer.tax import tax_of


def subtotal(lines: list[Line]) -> Decimal:
    """Gives the sum of the lines' exact amounts, never rounded, or Decimal 0 for no lines."""
    return sum((line.amount() for line in lines), Decimal(0))


def total(lines: list[Line], rate: Decimal) -> Decimal:
    """Gives the subtotal of lines with its tax at rate, a fraction such as Decimal('0.19'), the
    tax alone rounded to the cent, half up."""
    amount = subtotal(lines)
    return amount + tax_of(amount, rate)
