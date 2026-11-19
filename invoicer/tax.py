"""The rounding of a tax to the cent, half up, which the library's totals and render and the
colleague's printed page, page.py, all take."""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def tax_of(amount: Decimal, rate: Decimal) -> Decimal:
    """Gives the tax on amount at rate, a fraction such as Decimal('0.19') for 19%, rounded to
    the cent, half up, such as 0.005 to 0.01."""
    return (amount * rate).quantize(CENT, rounding=ROUND_HALF_UP)
