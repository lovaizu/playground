"""The Line, one line of an invoice, which carries both a library caller's lines and the
colleague's lines, from the sheet that sheet.py reads to the page that page.py lays out; and the
semicolon text in which library callers give lines."""

from __future__ import annotations

from decimal import Decimal
from typing import Union


class Line:
    """One line of an invoice: what it's for, its price, and how many.

    Takes: description, a str; price, a Decimal in the invoice's currency; quantity, an int or
    a Decimal, 1 where none is given. It keeps each as given, checking none."""

    def __init__(self, description: str, price: Decimal, quantity: Union[int, Decimal] = 1) -> None:
        self.description = description
        self.price = price
        self.quantity = quantity

    def amount(self) -> Decimal:
        """Gives price times quantity, exact, never rounded."""
        return self.price * self.quantity

    def __repr__(self) -> str:
        return f"Line({self.description!r}, {self.price!r}, {self.quantity!r})"


def parse_lines(text: str) -> list[Line]:
    """Gives a Line for each row of text, `<description>;<price>;<quantity>`, in the rows' order,
    or [] where text holds none: the description stripped of spaces around it, the price a
    Decimal, and the quantity an int. It skips each blank row, one empty or of spaces alone.

    Refuses: ValueError, where a row holds other than three fields or its quantity isn't a whole
    number; InvalidOperation of the decimal module, where its price isn't a number."""
    lines = []
    for row in text.splitlines():
        if not row.strip():
            continue
        description, price, quantity = row.split(";")
        lines.append(Line(description.strip(), Decimal(price), int(quantity)))
    return lines
