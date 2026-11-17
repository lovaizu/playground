"""The totals of an invoice."""

from decimal import Decimal

from invoicer.tax import tax_of


def subtotal(lines):
    """The sum of the lines' amounts."""
    return sum((line.amount() for line in lines), Decimal(0))


def total(lines, rate):
    """The sum of the lines' amounts with the tax at the rate."""
    amount = subtotal(lines)
    return amount + tax_of(amount, rate)
