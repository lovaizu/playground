"""The layout of the invoice as text."""

from decimal import Decimal

from invoicer.totals import line_amount, subtotal, tax, total


def render(lines, rate, currency="EUR"):
    """The invoice's text: a row for each line, then the subtotal, the tax, and the total, each
    amount as invoicer.totals states it, to the cent.

    Changed in 1.5.0: 1.4.0 showed each amount with the decimals it had, such as `89.5` or
    `37.035`, and a subtotal of the unrounded amounts.
    """
    rows = [_row(line.description, line_amount(line), currency) for line in lines]
    rows.append(_row("Subtotal", subtotal(lines), currency))
    rows.append(_row("Tax", tax(lines, rate), currency))
    rows.append(_row("Total", total(lines, rate), currency))
    return "\n".join(rows)


def _row(label: str, amount: Decimal, currency: str) -> str:
    """One row of the invoice: the label, then the amount in a column of its own."""
    return f"{label:<30}{amount:>12} {currency}"
