"""The amounts that an invoice states, each to the cent: each line's, the subtotal, the tax, and
the total, which the printed invoice and the package's callers both take from here. Each function
takes lines whose price is a Decimal or a whole number, and gives a Decimal."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from invoicer.lines import Line
from invoicer.tax import tax_of, to_cent


def line_amount(line: Line) -> Decimal:
    """The line's amount, its price times its quantity, rounded half up to the cent."""
    return to_cent(line.amount())


def subtotal(lines: Iterable[Line]) -> Decimal:
    """The sum of the lines' amounts as line_amount states them, so that the stated amounts add up
    to it; Decimal("0") where there's no line. The lines may be any iterable, a generator
    included, which it reads once.

    Changed in 1.5.0: 1.4.0 summed the unrounded amounts, which could differ by a cent.
    """
    return sum((line_amount(line) for line in lines), Decimal(0))


def tax(lines: Iterable[Line], rate: Decimal) -> Decimal:
    """The tax on the subtotal at the rate, a fraction such as Decimal("0.19"), to the cent. The
    lines may be any iterable, a generator included, which it reads once."""
    return tax_of(subtotal(lines), rate)


def total(lines: Iterable[Line], rate: Decimal) -> Decimal:
    """The subtotal and the tax at the rate, a fraction such as Decimal("0.19"), as stated. The
    lines may be any iterable, a generator included, which it reads once.

    Changed in 1.5.0: 1.4.0 added the tax to the unrounded subtotal, which could differ by a cent.
    """
    stated = subtotal(lines)
    return stated + tax_of(stated, rate)
