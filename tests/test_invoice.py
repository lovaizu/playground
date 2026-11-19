"""The unit cases of the invoice, invoice.make, with the library's own render beside it.

Each docstring names, after Supports, the integration case of tests/test_integration.py that it
supports.
"""

from __future__ import annotations

import random
import unittest
from datetime import date
from decimal import Decimal

from spreadsheet import WALKTHROUGH_INVOICE, WALKTHROUGH_ROWS

from invoicer import Line, invoice, render
from invoicer.invoice import Details, Invoice

WALKTHROUGH = [Line(*row) for row in WALKTHROUGH_ROWS[1:]]
NORDWIND = Details("Nordwind GmbH", "2026-031", "19", Decimal("0.19"))


def heading(details: Details, today: date) -> str:
    """The four lines that open an invoice, as the walkthrough shows them."""
    return (
        f"Invoice {details.number}\nClient: {details.client}\nDate: {today.isoformat()}\n"
        f"Tax rate: {details.rate_typed}%"
    )


class MakeTest(unittest.TestCase):
    """invoice.make on the lines, the details, and the date that the command hands it."""

    def text(self, lines: list[Line], details: Details, today: date) -> str:
        """The text of the invoice that make gives, without the line ends after it."""
        made = invoice.make(lines, details, today)
        self.assertIsInstance(made, Invoice)
        return made.text.rstrip("\n")

    def test_the_walkthroughs_invoice(self) -> None:
        """Supports: test_s1_prints_the_walkthrough_invoice.

        Given the walkthrough's three lines, Nordwind GmbH's details at 19, and 2026-11-19.
        When make makes the invoice.
        Then its text is the walkthrough's, to the last space.
        """
        today = date(2026, 11, 19)
        self.assertEqual(
            self.text(WALKTHROUGH, NORDWIND, today),
            WALKTHROUGH_INVOICE.format(today=today.isoformat()),
        )

    def test_the_sums_come_at_the_fraction_and_the_heading_shows_the_typed_rate(
        self,
    ) -> None:
        """Supports: test_s1_taxes_at_the_typed_rate.

        Given details whose typed rate is 19 and whose fraction is 0.07.
        When make makes the walkthrough's invoice.
        Then the heading says `Tax rate: 19%`, and the sums are those of the library at 0.07.
        """
        details = Details("Nordwind GmbH", "2026-031", "19", Decimal("0.07"))
        text = self.text(WALKTHROUGH, details, date(2026, 11, 19))
        self.assertIn("Tax rate: 19%\n", text)
        self.assertTrue(text.endswith(render(WALKTHROUGH, Decimal("0.07"))))

    def test_each_kind_of_typed_rate_shows_as_typed(self) -> None:
        """Supports: test_s1_taxes_at_the_typed_rate.

        Given a rate of 0, 100, or 19.5, the ends of the range and one with a decimal.
        When make makes the walkthrough's invoice.
        Then the heading shows the rate as typed, and the sums are the library's at its fraction.
        """
        for typed, fraction in (("0", "0"), ("100", "1"), ("19.5", "0.195")):
            with self.subTest(rate=typed):
                details = Details("Nordwind GmbH", "2026-031", typed, Decimal(fraction))
                text = self.text(WALKTHROUGH, details, date(2026, 11, 19))
                self.assertIn(f"Tax rate: {typed}%\n", text)
                self.assertTrue(text.endswith(render(WALKTHROUGH, Decimal(fraction))))

    def test_the_date_is_the_one_given(self) -> None:
        """Supports: test_s1_prints_the_walkthrough_invoice.

        Given the date 2027-01-02.
        When make makes the walkthrough's invoice.
        Then it says `Date: 2027-01-02`, whatever day it runs.
        """
        self.assertIn(
            "\nDate: 2027-01-02\n", self.text(WALKTHROUGH, NORDWIND, date(2027, 1, 2))
        )

    def test_one_line_gives_one_row(self) -> None:
        """Supports: test_s1_sums_are_the_library_sums.

        Given one line, the fewest that an invoice holds.
        When make makes the invoice.
        Then it shows the heading, a blank line, and the library's row and sums for that line.
        """
        lines = [Line("Payroll, October", Decimal("14.50"), 9)]
        today = date(2026, 11, 19)
        self.assertEqual(
            self.text(lines, NORDWIND, today),
            f"{heading(NORDWIND, today)}\n\n{render(lines, Decimal('0.19'))}",
        )

    def test_every_invoice_holds_the_librarys_sums(self) -> None:
        """Supports: test_s1_sums_are_the_library_sums.

        Given 300 drawn invoices of 1 to 300 lines each, at rates from 0 to 100.
        When make makes each.
        Then each text is its heading, a blank line, and the library's render of its lines at its
        fraction, with no counterexample.
        """
        draw = random.Random(1904)
        for each in range(300):
            lines = [
                Line(
                    f"Item {n}",
                    Decimal(draw.randint(0, 9999999)).scaleb(-2),
                    draw.randint(1, 999),
                )
                for n in range(draw.randint(1, 300))
            ]
            typed = f"{draw.randint(0, 100)}"
            details = Details(
                f"Client {each}", f"2026-{each:03}", typed, Decimal(typed) / 100
            )
            today = date.fromordinal(date(2026, 1, 1).toordinal() + each)
            with self.subTest(invoice=each):
                self.assertEqual(
                    self.text(lines, details, today),
                    f"{heading(details, today)}\n\n{render(lines, details.rate)}",
                )


if __name__ == "__main__":
    unittest.main()
