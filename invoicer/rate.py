"""How the percent the colleague types after --rate becomes the invoice's tax rate."""

import re
from decimal import Decimal

# A typed percent: digits with at most one decimal comma or point, then an optional %. sheet.py's
# _QUANTITY reads a quantity by a pattern alike but apart, as the sheet refuses `1.000` as a
# quantity, which reads two ways, where `19.000` here is 19%.
_PERCENT = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*%?")
_TYPE_A_PERCENT = "type the client's tax rate as a percent from 0 to 100, such as --rate 19"


class RateError(Exception):
    """A typed rate that gives no tax rate; its message says what to type instead."""


def parse_rate(text: str) -> Decimal:
    """Gives the rate of the typed percent as a fraction, such as `19` or `19%` -> Decimal('0.19').
    A decimal comma or point and a trailing %, with or without a space before it, are allowed,
    such as `19,5` or `19 %` -> Decimal('0.195'). 0 and 100 are the lowest and the highest.

    Refuses: RateError, for text that's empty or not a number, such as `nineteen` or `+19`; a
    number below 0 or more than 100; and one between 0 and 1, such as `0.19`, which is a
    fraction typed for a percent."""
    typed = text.strip()
    percent_match = _PERCENT.fullmatch(typed)
    if percent_match is None:
        raise RateError(f"the rate `{typed}` isn't a number: {_TYPE_A_PERCENT}")
    percent = Decimal(percent_match.group(1).replace(",", "."))
    if percent < 0 or percent > 100:
        raise RateError(f"the rate `{typed}` is outside 0 to 100: {_TYPE_A_PERCENT}")
    if 0 < percent < 1:
        raise RateError(
            f"the rate `{typed}` is below 1%: type the rate as a percent, such as 19 for 19%"
        )
    # copy_abs turns a typed `-0` into 0, so the page never reads `Tax -0%`.
    return percent.copy_abs().scaleb(-2)
