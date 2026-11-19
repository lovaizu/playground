"""Library regression: each public name of invoicer 1.4.0, for each class of what it takes, gives
what it gave in 1.4.0. These cases pass before anything new is built, and fail where a change
breaks a developer's call."""

import unittest
from decimal import Decimal, InvalidOperation

import invoicer


class LibraryGivesWhatItGave(unittest.TestCase):
    def test_parse_lines_skips_blank_rows(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given a text of two lines with a blank row between and spaces around a description.
        When parse_lines reads it.
        Then it gives the two Lines, stripped, with Decimal prices and int quantities."""
        lines = invoicer.parse_lines(" Kaffee ;2.50;4\n\nTee;1.20;1\n")

        self.assertEqual(
            [(l.description, l.price, l.quantity) for l in lines],
            [("Kaffee", Decimal("2.50"), 4), ("Tee", Decimal("1.20"), 1)],
        )

    def test_parse_lines_skips_a_row_of_spaces_alone(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given a text of two lines with a row of spaces alone between them.
        When parse_lines reads it.
        Then it gives the two Lines, the row of spaces skipped."""
        lines = invoicer.parse_lines("Kaffee;2.50;4\n   \nTee;1.20;1")

        self.assertEqual(
            [(l.description, l.price, l.quantity) for l in lines],
            [("Kaffee", Decimal("2.50"), 4), ("Tee", Decimal("1.20"), 1)],
        )

    def test_parse_lines_of_no_rows_gives_no_lines(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given an empty text.
        When parse_lines reads it.
        Then it gives []."""
        self.assertEqual(invoicer.parse_lines(""), [])

    def test_parse_lines_refuses_a_row_of_two_fields(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given a row `Kaffee;2.50`, its quantity left out.
        When parse_lines reads it.
        Then it refuses with ValueError."""
        with self.assertRaises(ValueError):
            invoicer.parse_lines("Kaffee;2.50")

    def test_parse_lines_refuses_a_row_of_four_fields(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given a row `Kaffee;2.50;4;EUR`, one field too many.
        When parse_lines reads it.
        Then it refuses with ValueError."""
        with self.assertRaises(ValueError):
            invoicer.parse_lines("Kaffee;2.50;4;EUR")

    def test_parse_lines_refuses_a_quantity_that_isnt_whole(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given a row `Beratung;80.00;2.5`, a quantity of two and a half.
        When parse_lines reads it.
        Then it refuses with ValueError."""
        with self.assertRaises(ValueError):
            invoicer.parse_lines("Beratung;80.00;2.5")

    def test_parse_lines_refuses_a_price_that_isnt_a_number(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given a row `Kaffee;two;4`, its price a word.
        When parse_lines reads it.
        Then it refuses with InvalidOperation of the decimal module."""
        with self.assertRaises(InvalidOperation):
            invoicer.parse_lines("Kaffee;two;4")

    def test_line_quantity_defaults_to_one(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given a Line made with no quantity.
        When amount gives its amount.
        Then the quantity is 1 and the amount its price."""
        line = invoicer.Line("Tee", Decimal("1.20"))

        self.assertEqual((line.quantity, line.amount()), (1, Decimal("1.20")))
        self.assertEqual(repr(line), "Line('Tee', Decimal('1.20'), 1)")

    def test_subtotal_of_no_lines_is_zero(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given no lines.
        When subtotal adds them.
        Then it gives Decimal 0."""
        self.assertEqual(invoicer.subtotal([]), Decimal(0))

    def test_tax_rounds_the_half_cent_up(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given an amount of 0.05 at 0.1, a tax of 0.005.
        When tax_of takes it.
        Then it gives 0.01."""
        self.assertEqual(invoicer.tax_of(Decimal("0.05"), Decimal("0.1")), Decimal("0.01"))

    def test_total_adds_the_rounded_tax(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given one line of 1.10 three times at 0.19.
        When total takes it.
        Then it gives 3.93."""
        self.assertEqual(invoicer.total(invoicer.parse_lines("x;1.10;3"), Decimal("0.19")), Decimal("3.93"))

    def test_render_defaults_to_eur(self):
        """Supports: LibraryKeepsItsNames.test_public_names_stay_and_give_what_they_gave

        Given one line of 2.50 four times at 0.07, and no currency.
        When render lays it out.
        Then each amount reads EUR, in the 1.4.0 layout."""
        self.assertEqual(
            invoicer.render(invoicer.parse_lines("Kaffee;2.50;4"), Decimal("0.07")),
            "Kaffee                               10.00 EUR\n"
            "Subtotal                             10.00 EUR\n"
            "Tax                                   0.70 EUR\n"
            "Total                                10.70 EUR",
        )


if __name__ == "__main__":
    unittest.main()
