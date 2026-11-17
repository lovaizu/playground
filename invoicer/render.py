"""The invoice as text."""

from decimal import Decimal

from invoicer.tax import tax_of, to_cent


def render(lines, rate, currency="EUR"):
    """The invoice's text: a row for each line, then the subtotal, the tax, and the total.

    It shows each amount to the cent, and the subtotal adds up the lines' amounts as it shows
    them, so that the printed rows add up, and the total is the subtotal and the tax as shown.
    """
    amounts = [to_cent(line.amount()) for line in lines]
    rows = [
        f"{line.description:<30}{amount:>12} {currency}" for line, amount in zip(lines, amounts)
    ]
    subtotal = sum(amounts, Decimal(0))
    tax = tax_of(subtotal, rate)
    rows.append(f"{'Subtotal':<30}{subtotal:>12} {currency}")
    rows.append(f"{'Tax':<30}{tax:>12} {currency}")
    rows.append(f"{'Total':<30}{subtotal + tax:>12} {currency}")
    return "\n".join(rows)
