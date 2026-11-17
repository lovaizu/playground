"""The lines of an invoice, and which rows of text, `<description>;<price>;<quantity>`, give one."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_SEPARATOR = ";"
# The form of a row, as messages and help show it to whoever saves the rows.
ROW = f"<description>{_SEPARATOR}<price>{_SEPARATOR}<quantity>"
# A quantity's digits; ASCII only, as int() would also take digits of other scripts.
_WHOLE = re.compile(r"[0-9]+")


class Line:
    """One line of an invoice: what it's for, its price, and how many."""

    def __init__(self, description: str, price: Decimal, quantity: int = 1) -> None:
        self.description = description
        self.price = price
        self.quantity = quantity

    def amount(self) -> Decimal:
        """The price times the quantity, unrounded."""
        return self.price * self.quantity

    def __repr__(self) -> str:
        return f"Line({self.description!r}, {self.price!r}, {self.quantity!r})"


class LineError(ValueError):
    """A row of text that gives no line; its message names the row and what's wrong with it."""


def parse_lines(text: str) -> list[Line]:
    """The lines of a text of one row each, `<description>;<price>;<quantity>`, as ROW shows it.

    Takes: the text, whose blank rows give no line. It drops the spaces around each field. The
    price is a finite number written with a point, such as `12.50`; the quantity a whole number
    from 1.
    Gives: one Line for each row that isn't blank, in the rows' order, or [] where every row is
    blank.
    Refuses: LineError, at the first row that has other than three fields, a price that isn't a
    finite number with a point, or a quantity that isn't a whole number from 1, naming the row by
    its number from 1, blank rows counted, as the spreadsheet that saved the text numbers them.
    """
    return [
        _line(number, row)
        for number, row in enumerate(text.splitlines(), start=1)
        if row.strip()
    ]


def _line(number: int, row: str) -> Line:
    """The line of row `number`, or LineError where it has other than three fields."""
    fields = [field.strip() for field in row.split(_SEPARATOR)]
    if len(fields) != 3:
        raise LineError(
            f"row {number}: a row must be {ROW}, three fields, not {len(fields)}: {row!r}"
        )
    description, price, quantity = fields
    return Line(description, _price(number, price), _quantity(number, quantity))


def _price(number: int, price: str) -> Decimal:
    """The price of row `number`, or LineError where it isn't a finite number."""
    try:
        value = Decimal(price)
    except InvalidOperation:
        value = None
    if value is None or not value.is_finite():
        raise LineError(
            f"row {number}: the price must be a number written with a point, such as 12.50, "
            f"not {price!r}"
        )
    return value


def _quantity(number: int, quantity: str) -> int:
    """The quantity of row `number`, or LineError where it isn't a whole number from 1."""
    if not _WHOLE.fullmatch(quantity) or int(quantity) < 1:
        raise LineError(
            f"row {number}: the quantity must be a whole number from 1, such as 3, "
            f"not {quantity!r}"
        )
    return int(quantity)
