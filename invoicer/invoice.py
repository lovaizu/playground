"""What one invoice shows: client, number, date, and typed rate, preceding the library's sums."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from invoicer import render
from invoicer.lines import Line


@dataclass(frozen=True)
class Details:
    """The values given for one invoice, which live only for the run that prints it.

    `client` and `number` are as typed, never empty. `rate_typed` is the rate in percent as
    typed, such as `"19"` for the heading. `rate` is the fraction that the command alone makes
    of it, such as Decimal("0.19"), for the library.
    """

    client: str
    number: str
    rate_typed: str
    rate: Decimal


@dataclass(frozen=True)
class Invoice:
    """One invoice as text, the same in the terminal and on paper."""

    text: str


def make(lines: Sequence[Line], details: Details, today: date) -> Invoice:
    """The invoice of the lines at the details' rate, dated `today`.

    Takes: the lines, at least one, from the spreadsheet reader or the sample; the details; and
    the date that the command hands it.
    Gives: an Invoice whose text shows `Invoice <number>`, `Client: <client>`, `Date: <today>`,
    and `Tax rate: <rate_typed>%`, then the rows and sums that the library's render gives for
    the lines and `details.rate` alone, in EUR.
    Changes: nothing.
    Refuses: nothing, as the command and the spreadsheet reader have checked each value.
    """
    heading = (
        f"Invoice {details.number}\n"
        f"Client: {details.client}\n"
        f"Date: {today.isoformat()}\n"
        f"Tax rate: {details.rate_typed}%"
    )
    return Invoice(f"{heading}\n\n{render(lines, details.rate, 'EUR')}")
