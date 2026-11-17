"""The lines of an invoice, and which rows of text, `<description>;<price>;<quantity>`, give one."""

from __future__ import annotations

import csv
import io
import re
from decimal import Decimal, InvalidOperation

_SEPARATOR = ";"
# The form of a row, as messages and help show it to whoever saves the rows.
ROW = f"<description>{_SEPARATOR}<price>{_SEPARATOR}<quantity>"
# A quantity, a minus allowed for a credit line, of at most 9 digits, so below _LIMIT; ASCII
# only, as int() would also take digits of other scripts.
_WHOLE = re.compile(r"-?[0-9]{1,9}")
# The size that a price and an amount must stay below either side of zero: far beyond any line
# of an invoice, so that a number past it is a mistyped cell, such as 1e400, and every sum of
# amounts stays exact to the cent.
_LIMIT = Decimal(1_000_000_000)
_BETWEEN = f"between -{_LIMIT} and {_LIMIT}"


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

    Takes: the text as a spreadsheet saves it as CSV with semicolons: a cell that holds a
    quotation mark, a semicolon or a new row of text is in quotes, with each quotation mark in it
    doubled, and is read as it was typed. A row whose cells are all empty or blank, such as `;;`,
    gives no line. It drops the spaces around each cell. The description must hold some text; the
    price is a number written with a point, such as `12.50`, or `-20.00` on a discount line; the
    quantity a whole number, such as `3`, or `0` or `-1` on a credit line; each, and the amount,
    the price times the quantity, between -1000000000 and 1000000000.
    Gives: one Line for each row that isn't blank, in the rows' order, or [] where every row is
    blank.
    Refuses: LineError, at the first wrong row, naming it by its number from 1, blank rows
    counted, as the spreadsheet that saved the text numbers them. A row is wrong where it has
    other than three fields, an empty description, a price that isn't a number with a point, a
    quantity that isn't a whole number, or a price, a quantity or an amount not between
    -1000000000 and 1000000000. The first row that isn't blank, where neither its price nor its
    quantity is a number, is refused as a heading, such as `Description;Price;Quantity`, with a
    message to leave the heading out.
    Changed in 1.5.0: 1.4.0 split each row of text at every semicolon, so it kept a quoted cell's
    quotes and refused a quoted cell holding a semicolon; it read an empty description and any
    number, such as 1e400; and it refused a wrong row, a heading and a row of empty cells among
    them, with a ValueError or an InvalidOperation of the decimal module that named no row,
    where it now raises LineError, a ValueError, or skips the row of empty cells.
    """
    # newline="" leaves a new row of text inside a quoted cell to csv, as its documentation asks.
    rows = csv.reader(io.StringIO(text, newline=""), delimiter=_SEPARATOR)
    lines = []
    first = True
    for number, cells in enumerate(rows, start=1):
        if all(not cell.strip() for cell in cells):
            continue
        lines.append(_line(number, cells, first))
        first = False
    return lines


def _line(number: int, cells: list[str], first: bool) -> Line:
    """The line of row `number`, or LineError where it gives none, the row being the first that
    isn't blank where `first`, so it may be a heading."""
    if len(cells) != 3:
        raise LineError(
            f"row {number}: a row must be {ROW}, three fields, not {len(cells)}: "
            f"{_SEPARATOR.join(cells)!r}"
        )
    description, price, quantity = (cell.strip() for cell in cells)
    if first and _number(price) is None and not _WHOLE.fullmatch(quantity):
        raise LineError(
            f"row {number}: a heading, as neither its price {price!r} nor its quantity "
            f"{quantity!r} is a number; save the lines without the heading row"
        )
    if not description:
        raise LineError(
            f"row {number}: the description is empty; write what the line is for, as the client "
            "reads it on the invoice"
        )
    line = Line(description, _price(number, price), _quantity(number, quantity))
    if abs(line.amount()) >= _LIMIT:
        raise LineError(
            f"row {number}: the amount, the price times the quantity, must be {_BETWEEN}, "
            f"not {line.amount()}"
        )
    return line


def _number(text: str) -> Decimal | None:
    """The finite number that the text writes, or None where it writes none."""
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _price(number: int, price: str) -> Decimal:
    """The price of row `number`, or LineError where it isn't a number below _LIMIT either side
    of zero."""
    value = _number(price)
    if value is None:
        raise LineError(
            f"row {number}: the price must be a number written with a point, such as 12.50, "
            f"not {price!r}"
        )
    if abs(value) >= _LIMIT:
        raise LineError(f"row {number}: the price must be {_BETWEEN}, not {price!r}")
    return value


def _quantity(number: int, quantity: str) -> int:
    """The quantity of row `number`, or LineError where it isn't a whole number below _LIMIT
    either side of zero."""
    if not _WHOLE.fullmatch(quantity):
        raise LineError(
            f"row {number}: the quantity must be a whole number {_BETWEEN}, such as 3, "
            f"or -1 on a credit line, not {quantity!r}"
        )
    return int(quantity)
