"""The unit and characterization cases of the library, which stays as invoicer 1.4.0 gives it.

Each docstring names, after Supports, the integration case of tests/test_integration.py that it
supports.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from invoicer import Line, parse_lines, render, subtotal, tax_of, total

WALKTHROUGH_TEXT = "Bookkeeping, October;85.00;12\n\nPayroll, October;14.50;9\nAnnual accounts 2025;450.00;1\n"


class LineTest(unittest.TestCase):
    """Line and parse_lines."""

    def test_a_lines_amount_is_its_price_times_its_quantity(self) -> None:
        """Supports: test_s4_gives_the_sums_and_text_of_1_4_0.

        Given a line of 14.50 times 9, and one with no quantity given.
        When each gives its amount.
        Then they are 130.50, and the price itself, as a quantity of 1.
        """
        self.assertEqual(str(Line("Payroll", Decimal("14.50"), 9).amount()), "130.50")
        self.assertEqual(
            str(Line("Annual accounts", Decimal("450.00")).amount()), "450.00"
        )
        self.assertEqual(
            repr(Line("Payroll", Decimal("14.50"), 9)),
            "Line('Payroll', Decimal('14.50'), 9)",
        )

    def test_parse_lines_reads_each_line_and_skips_blank_ones(self) -> None:
        """Supports: test_s4_gives_the_sums_and_text_of_1_4_0.

        Given the walkthrough's lines as text, a blank line among them.
        When parse_lines reads it.
        Then it gives the three lines, each price a Decimal and each quantity a whole number.
        """
        got = [
            (line.description, line.price, line.quantity)
            for line in parse_lines(WALKTHROUGH_TEXT)
        ]
        self.assertEqual(
            got,
            [
                ("Bookkeeping, October", Decimal("85.00"), 12),
                ("Payroll, October", Decimal("14.50"), 9),
                ("Annual accounts 2025", Decimal("450.00"), 1),
            ],
        )


class SumsTest(unittest.TestCase):
    """tax_of, subtotal, total, and render."""

    def test_the_tax_rounds_half_up_to_the_cent(self) -> None:
        """Supports: test_s4_gives_the_sums_and_text_of_1_4_0.

        Given 304.095, at the half cent, and the amounts just beside it.
        When tax_of counts them at the rate 1.
        Then 304.095 rounds up to 304.10, 304.0949 down to 304.09, and 304.0951 up to 304.10.
        """
        for amount, tax in (
            ("304.095", "304.10"),
            ("304.0949", "304.09"),
            ("304.0951", "304.10"),
        ):
            with self.subTest(amount=amount):
                self.assertEqual(str(tax_of(Decimal(amount), Decimal(1))), tax)
        self.assertEqual(str(tax_of(Decimal("1600.50"), Decimal("0.19"))), "304.10")

    def test_the_sums_of_no_line_are_0(self) -> None:
        """Supports: test_s4_gives_the_sums_and_text_of_1_4_0.

        Given no line.
        When subtotal and total count them at 0.19.
        Then each is 0.
        """
        self.assertEqual(
            (subtotal([]), total([], Decimal("0.19"))), (Decimal(0), Decimal(0))
        )

    def test_render_gives_1_4_0s_text(self) -> None:
        """Supports: test_s4_gives_the_sums_and_text_of_1_4_0.

        Given the walkthrough's lines at 0.19, in EUR and in USD.
        When render gives their text.
        Then each row is the description to 30 places and the amount to 12, then the currency.
        """
        lines = parse_lines(WALKTHROUGH_TEXT)
        self.assertEqual(
            render(lines, Decimal("0.19")).splitlines()[-1],
            f"{'Total':<30}{'1904.60':>12} EUR",
        )
        self.assertEqual(
            render(lines, Decimal("0.19"), currency="USD").splitlines()[0],
            f"{'Bookkeeping, October':<30}{'1020.00':>12} USD",
        )


if __name__ == "__main__":
    unittest.main()
