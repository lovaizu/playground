"""Tests of reading an invoice's lines from rows of text, which support the command's case
test_prints_nothing_when_a_row_is_wrong."""

import unittest
from decimal import Decimal

from invoicer.lines import LineError, parse_lines


class ParseLinesTest(unittest.TestCase):
    def test_reads_each_row_as_a_line(self):
        # Given two rows, when parse_lines reads them, then each gives its line, in order.
        lines = parse_lines("Design ;100.00;2\nHosting;10.50;1\n")

        self.assertEqual(
            [(line.description, line.price, line.quantity) for line in lines],
            [("Design", Decimal("100.00"), 2), ("Hosting", Decimal("10.50"), 1)],
        )

    def test_skips_a_blank_row(self):
        lines = parse_lines("Design;100.00;2\n\n   \nHosting;10.50;1")

        self.assertEqual([line.description for line in lines], ["Design", "Hosting"])

    def test_gives_no_line_for_a_text_of_blank_rows(self):
        self.assertEqual(parse_lines("\n \n"), [])

    def test_refuses_a_row_of_two_fields_naming_it(self):
        # Row 3 counts the blank row 2, as the spreadsheet numbers it.
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;100.00;2\n\nHosting;10.50")

        self.assertEqual(
            str(refused.exception),
            "row 3: a row must be <description>;<price>;<quantity>, three fields, "
            "not 2: 'Hosting;10.50'",
        )

    def test_refuses_a_price_written_with_a_comma_naming_the_row(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;100,00;2")

        self.assertEqual(
            str(refused.exception),
            "row 1: the price must be a number written with a point, such as 12.50, "
            "not '100,00'",
        )

    def test_refuses_a_price_that_is_not_finite(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;NaN;2")

        self.assertEqual(
            str(refused.exception),
            "row 1: the price must be a number written with a point, such as 12.50, not 'NaN'",
        )

    def test_refuses_a_quantity_that_is_not_whole(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;100.00;2.5")

        self.assertEqual(
            str(refused.exception),
            "row 1: the quantity must be a whole number from 1, such as 3, not '2.5'",
        )

    def test_refuses_a_quantity_of_zero(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;100.00;0")

        self.assertEqual(
            str(refused.exception),
            "row 1: the quantity must be a whole number from 1, such as 3, not '0'",
        )

    def test_takes_a_quantity_of_one(self):
        (line,) = parse_lines("Design;100.00;1")

        self.assertEqual(line.quantity, 1)


if __name__ == "__main__":
    unittest.main()
