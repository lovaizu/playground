"""The invoice as text."""

from invoicer.tax import tax_of
from invoicer.totals import subtotal


def render(lines, rate, currency="EUR"):
    """The invoice's text: a row for each line, then the subtotal, the tax, and the total."""
    rows = [f"{line.description:<30}{line.amount():>12} {currency}" for line in lines]
    amount = subtotal(lines)
    tax = tax_of(amount, rate)
    rows.append(f"{'Subtotal':<30}{amount:>12} {currency}")
    rows.append(f"{'Tax':<30}{tax:>12} {currency}")
    rows.append(f"{'Total':<30}{amount + tax:>12} {currency}")
    return "\n".join(rows)
