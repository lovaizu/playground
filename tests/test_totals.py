"""Tests of the amounts that an invoice states, which support the command's cases
test_prints_each_amount_to_the_cent and test_prints_a_subtotal_that_adds_up_the_amounts_as_printed,
so that the printed invoice and the package's subtotal and total give the same figures."""

import unittest
from decimal import Decimal

from invoicer import Line, render, subtotal, total
from invoicer.totals import line_amount, tax

RATE = Decimal("0.19")
# Three lines of 0.005 each, each stated as 0.01, whose unrounded sum 0.015 differs from 0.03.
HALF_CENTS = [
    Line("Pen", Decimal("0.005"), 1),
    Line("Pencil", Decimal("0.005"), 1),
    Line("Eraser", Decimal("0.005"), 1),
]


class TotalsTest(unittest.TestCase):
    def test_states_a_line_amount_to_the_cent(self):
        # Given 12.345 times 3, then the amount is 37.035 rounded half up to 37.04.
        amount = line_amount(Line("Support", Decimal("12.345"), 3))

        self.assertEqual(str(amount), "37.04")

    def test_subtotal_adds_the_amounts_as_stated(self):
        self.assertEqual(str(subtotal(HALF_CENTS)), "0.03")

    def test_tax_is_that_of_the_subtotal_as_stated(self):
        # 0.03 at 19 percent is 0.0057, rounded to 0.01.
        self.assertEqual(str(tax(HALF_CENTS, RATE)), "0.01")

    def test_total_is_the_subtotal_and_the_tax_as_stated(self):
        self.assertEqual(str(total(HALF_CENTS, RATE)), "0.04")

    def test_subtotal_of_a_generator_of_lines_adds_its_amounts(self):
        self.assertEqual(str(subtotal(line for line in HALF_CENTS)), "0.03")

    def test_tax_of_a_generator_of_lines_is_that_of_its_subtotal(self):
        self.assertEqual(str(tax((line for line in HALF_CENTS), RATE)), "0.01")

    def test_total_of_a_generator_of_lines_adds_the_tax(self):
        # Given 20.00 of lines at 19 percent, then the total is 23.80, as 1.4.0 gave, not the
        # subtotal 20.00 alone.
        lines = (line for line in [Line("Design", Decimal("10.00"), 2)])

        self.assertEqual(str(total(lines, RATE)), "23.80")

    def test_render_of_a_generator_of_lines_prints_their_subtotal_and_total(self):
        printed = render((line for line in HALF_CENTS), RATE).splitlines()

        self.assertEqual(
            printed[-3:],
            [
                "Subtotal".ljust(30) + "0.03".rjust(12) + " EUR",
                "Tax".ljust(30) + "0.01".rjust(12) + " EUR",
                "Total".ljust(30) + "0.04".rjust(12) + " EUR",
            ],
        )

    def test_render_prints_the_subtotal_and_total_that_the_package_gives(self):
        # Supports test_prints_a_subtotal_that_adds_up_the_amounts_as_printed.
        printed = render(HALF_CENTS, RATE).splitlines()

        self.assertEqual(
            printed[-3:],
            [
                "Subtotal".ljust(30) + "0.03".rjust(12) + " EUR",
                "Tax".ljust(30) + "0.01".rjust(12) + " EUR",
                "Total".ljust(30) + "0.04".rjust(12) + " EUR",
            ],
        )


if __name__ == "__main__":
    unittest.main()
