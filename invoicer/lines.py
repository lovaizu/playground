"""The lines of an invoice."""

from decimal import Decimal


class Line:
    """One line of an invoice: what it's for, its price, and how many."""

    def __init__(self, description, price, quantity=1):
        self.description = description
        self.price = price
        self.quantity = quantity

    def amount(self):
        return self.price * self.quantity

    def __repr__(self):
        return f"Line({self.description!r}, {self.price!r}, {self.quantity!r})"


def parse_lines(text):
    """The lines of a text of one line each, `<description>;<price>;<quantity>`."""
    found = []
    for row in text.splitlines():
        if not row.strip():
            continue
        description, price, quantity = row.split(";")
        found.append(Line(description.strip(), Decimal(price), int(quantity)))
    return found
