"""The rounding to the cent of an amount, and of the tax of an amount."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def to_cent(amount):
    """The amount, a Decimal or a whole number, rounded half up to the cent, such as 37.04 for
    37.035 and 100.00 for 100."""
    # Decimal() reads a whole number exactly, as a line built with a price such as 50 gives one.
    return Decimal(amount).quantize(CENT, rounding=ROUND_HALF_UP)


def tax_of(amount, rate):
    """The tax on the amount at the rate, rounded to the cent."""
    return to_cent(amount * rate)
