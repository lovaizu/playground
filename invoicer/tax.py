"""The tax of an amount."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def tax_of(amount, rate):
    """The tax on the amount at the rate, rounded to the cent."""
    return (amount * rate).quantize(CENT, rounding=ROUND_HALF_UP)
