"""The invoice as text for library callers, a row per line and the totals, in 1.4.0's layout;
the colleague's printed invoice is page.py's, from the sheet that sheet.py reads."""

from __future__ import annotations

from decimal import Decimal

from invoicer.lines import Line
from invoicer.tax import tax_of
from invoicer.totals import subtotal


def render(lines: list[Line], rate: Decimal, currency: str = "EUR") -> str:
    """Gives the invoice's text: a row for each line with its description in 30 characters and
    its exact amount in 12, then Subtotal, Tax, and Total rows, each amount followed by currency,
    the rows joined by newlines with none at the end. rate is a fraction, such as
    Decimal('0.19'); only the tax is rounded, to the cent, half up. For no lines, it gives the
    three totals rows alone."""
    rows = [f"{line.description:<30}{line.amount():>12} {currency}" for line in lines]
    amount = subtotal(lines)
    tax = tax_of(amount, rate)
    rows.append(f"{'Subtotal':<30}{amount:>12} {currency}")
    rows.append(f"{'Tax':<30}{tax:>12} {currency}")
    rows.append(f"{'Total':<30}{amount + tax:>12} {currency}")
    return "\n".join(rows)
