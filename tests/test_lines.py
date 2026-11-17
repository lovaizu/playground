"""Tests of reading an invoice's lines from rows of text, which support the command's cases
test_prints_nothing_when_a_row_is_wrong, test_prints_a_credit_line and
test_refuses_a_price_too_large_to_print."""

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

    def test_reads_a_cell_saved_in_quotes_as_typed(self):
        # Supports test_prints_a_description_saved_in_quotes_as_typed.
        (line,) = parse_lines('"Design ""Pro""";100.00;2')

        self.assertEqual(line.description, 'Design "Pro"')

    def test_reads_a_cell_holding_a_semicolon_saved_in_quotes(self):
        # Supports test_prints_a_description_holding_a_semicolon.
        (line,) = parse_lines('"Design; phase 1";100.00;2')

        self.assertEqual(
            (line.description, line.price, line.quantity),
            ("Design; phase 1", Decimal("100.00"), 2),
        )

    def test_numbers_a_row_after_a_cell_holding_a_new_row(self):
        # Given a cell typed on two rows of text, which the spreadsheet keeps in one row, then
        # the next row is numbered as the spreadsheet numbers it, 2. Supports
        # test_prints_nothing_when_a_row_is_wrong.
        with self.assertRaises(LineError) as refused:
            parse_lines('"Design\nphase 1";100.00;2\nSupport;ten;1')

        self.assertIn("row 2:", str(refused.exception), "the row is numbered as in the spreadsheet")

    def test_refuses_a_quotation_mark_that_never_closes_naming_the_row_where_it_opens(self):
        # Given row 2 whose cell opens with a quotation mark that no mark closes, then the refusal
        # names row 2, not the rest of the text read into one cell. Supports
        # test_refuses_a_quotation_mark_that_never_closes_naming_the_row_where_it_opens.
        with self.assertRaises(LineError) as refused:
            parse_lines('Design;100.00;2\n"Pro;10.50;1\nSupport;5.00;1\n')

        self.assertEqual(
            str(refused.exception),
            "row 2: a cell starts with a quotation mark but doesn't end with one that closes it; "
            "remove that mark, or end the cell with one and write each quotation mark inside it "
            "twice",
        )

    def test_refuses_a_quotation_mark_that_never_closes_in_a_long_file(self):
        # Given 30000 rows after the mark, more than the csv module holds in one cell, then
        # parse_lines refuses it as in a short file, with no error of the csv module. Supports
        # test_refuses_a_quotation_mark_that_never_closes_naming_the_row_where_it_opens.
        with self.assertRaises(LineError) as refused:
            parse_lines('Design;100.00;2\n"Pro;10.50;1\n' + "Support;5.00;1\n" * 30000)

        self.assertEqual(
            str(refused.exception),
            "row 2: a cell starts with a quotation mark but doesn't end with one that closes it; "
            "remove that mark, or end the cell with one and write each quotation mark inside it "
            "twice",
        )

    def test_refuses_a_cell_with_text_after_its_closing_quotation_mark(self):
        # Given `"Pro" x`, which reads in no one way and a spreadsheet never saves, then row 2 is
        # refused, not read as `Pro x`. Supports
        # test_refuses_a_quotation_mark_that_never_closes_naming_the_row_where_it_opens.
        with self.assertRaises(LineError) as refused:
            parse_lines('Design;100.00;2\n"Pro" x;10.50;1\n')

        self.assertEqual(
            str(refused.exception),
            "row 2: a cell starts with a quotation mark but doesn't end with one that closes it; "
            "remove that mark, or end the cell with one and write each quotation mark inside it "
            "twice",
        )

    def test_reads_a_quotation_mark_inside_a_cell_that_starts_without_one(self):
        # Given `5" screen`, typed with no quotes around the cell, then the mark is read as typed.
        (line,) = parse_lines('5" screen;120.00;1')

        self.assertEqual(line.description, '5" screen')

    def test_skips_a_row_of_empty_cells(self):
        # Supports test_skips_a_row_whose_cells_are_all_empty.
        lines = parse_lines("Design;100.00;2\n;;\n ; ; \nHosting;10.50;1")

        self.assertEqual([line.description for line in lines], ["Design", "Hosting"])

    def test_refuses_a_heading_row_naming_it(self):
        # Supports test_refuses_a_heading_row_asking_to_leave_it_out; the blank row 1 is counted.
        with self.assertRaises(LineError) as refused:
            parse_lines("\nDescription;Price;Quantity\nDesign;100.00;2")

        self.assertEqual(
            str(refused.exception),
            "row 2: a heading, as neither its price 'Price' nor its quantity 'Quantity' is a "
            "number; save the lines without the heading row",
        )

    def test_refuses_a_wrong_price_on_the_first_row_as_a_price(self):
        # Given a first row whose quantity is a number, then it isn't taken for a heading.
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;ten;1")

        self.assertEqual(
            str(refused.exception),
            "row 1: the price must be a number written with a point, such as 12.50, not 'ten'",
        )

    def test_refuses_a_row_after_the_first_as_a_price_not_a_heading(self):
        # Given a row after the first with neither price nor quantity a number, then it is
        # refused for its price, as only the first row can be the heading.
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;100.00;2\nSupport;ten;three")

        self.assertEqual(
            str(refused.exception),
            "row 2: the price must be a number written with a point, such as 12.50, not 'ten'",
        )

    def test_refuses_an_empty_description_naming_the_row(self):
        # Supports test_refuses_a_row_with_an_empty_description.
        with self.assertRaises(LineError) as refused:
            parse_lines("  ;100.00;2")

        self.assertEqual(
            str(refused.exception),
            "row 1: the description is empty; write what the line is for, as the client reads "
            "it on the invoice",
        )

    def test_refuses_a_row_of_two_fields_naming_it(self):
        # Row 3 counts the blank row 2, as the spreadsheet numbers it.
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;100.00;2\n\nHosting;10.50")

        self.assertEqual(
            str(refused.exception),
            "row 3: a row must be <description>;<price>;<quantity>, three fields, "
            "not 2: 'Hosting;10.50'",
        )

    def test_refuses_a_row_of_four_fields_naming_it(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;100.00;2;paid")

        self.assertEqual(
            str(refused.exception),
            "row 1: a row must be <description>;<price>;<quantity>, three fields, "
            "not 4: 'Design;100.00;2;paid'",
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

    def test_refuses_a_price_too_large_to_print(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;1e400;1")

        self.assertEqual(
            str(refused.exception),
            "row 1: the price must be between -1000000000 and 1000000000, not '1e400'",
        )

    def test_takes_a_price_just_below_the_limit(self):
        (line,) = parse_lines("Design;999999999.99;1")

        self.assertEqual(line.price, Decimal("999999999.99"))

    def test_refuses_a_price_at_the_limit(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;1000000000;0")

        self.assertEqual(
            str(refused.exception),
            "row 1: the price must be between -1000000000 and 1000000000, not '1000000000'",
        )

    def test_refuses_a_price_at_the_negative_limit(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Discount;-1000000000;1")

        self.assertIn("not '-1000000000'", str(refused.exception), "the refused price is named")

    def test_reads_a_negative_price_as_on_a_discount_line(self):
        (line,) = parse_lines("Discount;-20.00;1")

        self.assertEqual((line.price, line.quantity), (Decimal("-20.00"), 1))

    def test_reads_a_negative_quantity_as_on_a_credit_line(self):
        (line,) = parse_lines("Returned hosting;10.50;-1")

        self.assertEqual((line.price, line.quantity), (Decimal("10.50"), -1))

    def test_reads_a_quantity_of_zero(self):
        (line,) = parse_lines("Cancelled;50.00;0")

        self.assertEqual(line.quantity, 0)

    def test_refuses_a_quantity_that_is_not_whole(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;100.00;2.5")

        self.assertEqual(
            str(refused.exception),
            "row 1: the quantity must be a whole number between -1000000000 and 1000000000, "
            "such as 3, or -1 on a credit line, not '2.5'",
        )

    def test_takes_a_quantity_just_below_the_limit(self):
        (line,) = parse_lines("Sample;0.00;999999999")

        self.assertEqual(line.quantity, 999999999)

    def test_refuses_a_quantity_at_the_limit(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Sample;0.00;1000000000")

        self.assertIn("not '1000000000'", str(refused.exception), "the refused quantity is named")

    def test_takes_an_amount_just_below_the_limit(self):
        (line,) = parse_lines("Design;499999999.99;2")

        self.assertEqual(line.amount(), Decimal("999999999.98"))

    def test_refuses_an_amount_at_the_limit(self):
        with self.assertRaises(LineError) as refused:
            parse_lines("Design;500000000.00;2")

        self.assertEqual(
            str(refused.exception),
            "row 1: the amount, the price times the quantity, must be between -1000000000 and "
            "1000000000, not 1000000000.00",
        )


if __name__ == "__main__":
    unittest.main()
