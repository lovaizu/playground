"""The tax of an amount, and how money is rounded to the cent."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def round_to_cent(amount):
    """The amount rounded half up to the cent."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def tax_of(amount, rate):
    """The tax on the amount at the rate, rounded to the cent."""
    return round_to_cent(amount * rate)
