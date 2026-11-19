"""Unit cases of page.render_page: the guide's page, and each class of details, lines, and rate it
lays out, every invoice in EUR. Each case compares the whole page."""

import unittest
from decimal import Decimal

from invoicer import page
from invoicer.lines import Line
from invoicer.sheet import Details
from tests import helpers

NORDWIND = Details(
    invoice_number="2026-041",
    date="2026-11-19",
    client_name="Nordwind Handel GmbH",
    client_address="Hafenweg 12, 20457 Hamburg",
    our_name="Lindqvist Buchhaltung GmbH",
    our_address="Hauptstraße 5, 10115 Berlin",
    our_vat_id="DE123456789",
)

# The rows of Nordwind's details that head each page, before its header row.
HEAD = (
    "Lindqvist Buchhaltung GmbH\n"
    "Hauptstraße 5, 10115 Berlin\n"
    "VAT ID DE123456789\n"
    "\n"
    "Nordwind Handel GmbH\n"
    "Hafenweg 12, 20457 Hamburg\n"
    "\n"
    "Invoice 2026-041\n"
    "Date 2026-11-19\n"
    "\n"
)


def nordwind_lines():
    return [Line(*line) for line in helpers.NORDWIND_LINES]


class PageCase(unittest.TestCase):
    def render(self, lines, rate):
        text = page.render_page(NORDWIND, lines, Decimal(rate))
        self.assertIsInstance(text, str)
        return text


class LaysOutThePage(PageCase):
    def test_nordwind_page_is_the_guides(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the Nordwind details, its three lines, and the rate 0.19.
        When render_page makes the page.
        Then it is the page that the guide's Walkthrough shows, with a newline at its end."""
        self.assertEqual(self.render(nordwind_lines(), "0.19"), helpers.guide_page() + "\n")

    def test_page_ends_with_one_newline(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the Nordwind details, its three lines, and the rate 0.19.
        When render_page makes the page.
        Then the page's last row, the Total, ends with one newline, and no empty row follows."""
        text = self.render(nordwind_lines(), "0.19")

        self.assertTrue(text.endswith("1429.19 EUR\n"), text[-20:])

    def test_each_line_shows_quantity_unit_price_and_amount(self):
        """Supports: PrintsTheInvoice.test_page_the_printer_gets_is_made_from_the_sheets_details_lines_and_rate

        Given a line of 3 stamps at 0.10, at the rate 0.19.
        When render_page makes the page.
        Then the details head it, its row shows 3, 0.10 EUR, and 0.30 EUR, and the subtotal is
        0.30 EUR, the tax 0.06 EUR, and the total 0.36 EUR."""
        text = self.render([Line("Stamp", Decimal("0.10"), 3)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price      Amount\n"
            + "Stamp                        3      0.10 EUR    0.30 EUR\n"
            + "\n"
            + "Subtotal                                        0.30 EUR\n"
            + "Tax 19%                                         0.06 EUR\n"
            + "Total                                           0.36 EUR\n"
        )

    def test_whole_price_shows_its_cents(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given a line whose price is Decimal 80, as Calc stores 80.00, of the whole quantity 10.
        When render_page makes the page.
        Then its row shows 10, 80.00 EUR, and 800.00 EUR."""
        text = self.render([Line("Bookkeeping hours", Decimal("80"), 10)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price        Amount\n"
            + "Bookkeeping hours           10     80.00 EUR    800.00 EUR\n"
            + "\n"
            + "Subtotal                                        800.00 EUR\n"
            + "Tax 19%                                         152.00 EUR\n"
            + "Total                                           952.00 EUR\n"
        )

    def test_tax_row_names_the_rate_as_a_percent(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given the Nordwind lines at the rate 0.075.
        When render_page makes the page.
        Then the tax row reads `Tax 7.5%` with 90.08 EUR, 1201.00 x 0.075 rounded half up."""
        text = self.render(nordwind_lines(), "0.075")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price         Amount\n"
            + "Bookkeeping hours           10     80.00 EUR     800.00 EUR\n"
            + "Annual accounts              1    350.00 EUR     350.00 EUR\n"
            + "Travel to client             2     25.50 EUR      51.00 EUR\n"
            + "\n"
            + "Subtotal                                        1201.00 EUR\n"
            + "Tax 7.5%                                          90.08 EUR\n"
            + "Total                                           1291.08 EUR\n"
        )

    def test_tax_at_zero(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given the Nordwind lines at the rate 0, the lowest.
        When render_page makes the page.
        Then the tax row reads `Tax 0%` and 0.00 EUR, and the total is the subtotal."""
        text = self.render(nordwind_lines(), "0")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price         Amount\n"
            + "Bookkeeping hours           10     80.00 EUR     800.00 EUR\n"
            + "Annual accounts              1    350.00 EUR     350.00 EUR\n"
            + "Travel to client             2     25.50 EUR      51.00 EUR\n"
            + "\n"
            + "Subtotal                                        1201.00 EUR\n"
            + "Tax 0%                                             0.00 EUR\n"
            + "Total                                           1201.00 EUR\n"
        )

    def test_tax_at_hundred(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given the Nordwind lines at the rate 1, the highest.
        When render_page makes the page.
        Then the tax row reads `Tax 100%` and 1201.00 EUR, and the total is 2402.00 EUR."""
        text = self.render(nordwind_lines(), "1")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price         Amount\n"
            + "Bookkeeping hours           10     80.00 EUR     800.00 EUR\n"
            + "Annual accounts              1    350.00 EUR     350.00 EUR\n"
            + "Travel to client             2     25.50 EUR      51.00 EUR\n"
            + "\n"
            + "Subtotal                                        1201.00 EUR\n"
            + "Tax 100%                                        1201.00 EUR\n"
            + "Total                                           2402.00 EUR\n"
        )

    def test_tax_on_the_half_cent_rounds_up(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given one line of 0.35 at the rate 0.10, a tax of 0.035.
        When render_page makes the page.
        Then the tax is 0.04 EUR and the total 0.39 EUR."""
        text = self.render([Line("Stamps", Decimal("0.35"), 1)], "0.10")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price      Amount\n"
            + "Stamps                       1      0.35 EUR    0.35 EUR\n"
            + "\n"
            + "Subtotal                                        0.35 EUR\n"
            + "Tax 10%                                         0.04 EUR\n"
            + "Total                                           0.39 EUR\n"
        )

    def test_tax_below_the_half_cent_rounds_down(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given one line of 0.34 at the rate 0.10, a tax of 0.034.
        When render_page makes the page.
        Then the tax is 0.03 EUR and the total 0.37 EUR."""
        text = self.render([Line("Stamps", Decimal("0.34"), 1)], "0.10")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price      Amount\n"
            + "Stamps                       1      0.34 EUR    0.34 EUR\n"
            + "\n"
            + "Subtotal                                        0.34 EUR\n"
            + "Tax 10%                                         0.03 EUR\n"
            + "Total                                           0.37 EUR\n"
        )


class RoundsEachFigureToTheCent(PageCase):
    def test_unit_price_past_the_cent_shows_rounded_to_the_cent(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given one line whose price a formula gave as 400.333333333333, which Calc shows as
        400.33, at the rate 0.19.
        When render_page makes the page.
        Then the unit price and the amount show 400.33 EUR, the tax 76.06 EUR, and the total
        476.39 EUR."""
        text = self.render([Line("Annual accounts", Decimal("400.333333333333"), 1)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price        Amount\n"
            + "Annual accounts              1    400.33 EUR    400.33 EUR\n"
            + "\n"
            + "Subtotal                                        400.33 EUR\n"
            + "Tax 19%                                          76.06 EUR\n"
            + "Total                                           476.39 EUR\n"
        )

    def test_unit_price_on_the_half_cent_rounds_up(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given one line at the price 0.125, on the half cent, at the rate 0.19.
        When render_page makes the page.
        Then the unit price and the amount show 0.13 EUR."""
        text = self.render([Line("Stamp", Decimal("0.125"), 1)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price      Amount\n"
            + "Stamp                        1      0.13 EUR    0.13 EUR\n"
            + "\n"
            + "Subtotal                                        0.13 EUR\n"
            + "Tax 19%                                         0.02 EUR\n"
            + "Total                                           0.15 EUR\n"
        )

    def test_amount_is_the_quantity_times_the_shown_price(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given one line of 3 at the price 0.125, shown as 0.13.
        When render_page makes the page.
        Then the amount is 3 x 0.13, 0.39 EUR, not 0.375 rounded to 0.38, so the row adds up."""
        text = self.render([Line("Stamp", Decimal("0.125"), 3)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price      Amount\n"
            + "Stamp                        3      0.13 EUR    0.39 EUR\n"
            + "\n"
            + "Subtotal                                        0.39 EUR\n"
            + "Tax 19%                                         0.07 EUR\n"
            + "Total                                           0.46 EUR\n"
        )

    def test_amount_on_the_half_cent_rounds_up(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given one line of 2.5 at 0.35, an amount of 0.875.
        When render_page makes the page.
        Then the amount shows 0.88 EUR, the tax 0.17 EUR, and the total 1.05 EUR."""
        text = self.render([Line("Receipts filed", Decimal("0.35"), Decimal("2.5"))], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price      Amount\n"
            + "Receipts filed             2.5      0.35 EUR    0.88 EUR\n"
            + "\n"
            + "Subtotal                                        0.88 EUR\n"
            + "Tax 19%                                         0.17 EUR\n"
            + "Total                                           1.05 EUR\n"
        )

    def test_subtotal_is_the_sum_of_the_shown_amounts(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given two lines of 1 at 0.125, each shown as 0.13.
        When render_page makes the page.
        Then the subtotal is 0.26 EUR, the sum of the shown amounts, not 0.25, the tax 0.05 EUR,
        and the total 0.31 EUR."""
        text = self.render(
            [Line("Stamp", Decimal("0.125"), 1), Line("Envelope", Decimal("0.125"), 1)], "0.19"
        )

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price      Amount\n"
            + "Stamp                        1      0.13 EUR    0.13 EUR\n"
            + "Envelope                     1      0.13 EUR    0.13 EUR\n"
            + "\n"
            + "Subtotal                                        0.26 EUR\n"
            + "Tax 19%                                         0.05 EUR\n"
            + "Total                                           0.31 EUR\n"
        )


class LaysOutWhatAccountingKeeps(PageCase):
    def test_quantity_of_hours_with_a_half(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a line of 2.5 hours at 80.00.
        When render_page makes the page.
        Then its row shows 2.5, 80.00 EUR, and 200.00 EUR."""
        text = self.render([Line("Bookkeeping hours", Decimal("80.00"), Decimal("2.5"))], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price        Amount\n"
            + "Bookkeeping hours          2.5     80.00 EUR    200.00 EUR\n"
            + "\n"
            + "Subtotal                                        200.00 EUR\n"
            + "Tax 19%                                          38.00 EUR\n"
            + "Total                                           238.00 EUR\n"
        )

    def test_quantity_of_many_decimal_places_shows_without_an_exponent(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a line of a quantity of 0.0000001 at 80.00, which Python writes as 1E-7.
        When render_page makes the page.
        Then its row shows the quantity as 0.0000001, the Quantity column widened to it, and an
        amount of 0.00 EUR."""
        line = Line("Bookkeeping hours", Decimal("80.00"), Decimal("0.0000001"))
        text = self.render([line], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description            Quantity    Unit price      Amount\n"
            + "Bookkeeping hours     0.0000001     80.00 EUR    0.00 EUR\n"
            + "\n"
            + "Subtotal                                         0.00 EUR\n"
            + "Tax 19%                                          0.00 EUR\n"
            + "Total                                            0.00 EUR\n"
        )

    def test_line_at_no_price(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a free first consultation, one at 0.
        When render_page makes the page.
        Then its row shows 0.00 EUR as its unit price and its amount, and every total is 0.00
        EUR."""
        text = self.render([Line("First consultation", Decimal("0"), 1)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price      Amount\n"
            + "First consultation           1      0.00 EUR    0.00 EUR\n"
            + "\n"
            + "Subtotal                                        0.00 EUR\n"
            + "Tax 19%                                         0.00 EUR\n"
            + "Total                                           0.00 EUR\n"
        )

    def test_discount_line_takes_off_the_subtotal(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given annual accounts at 350.00 and an early payment discount at -50.00, at 19%.
        When render_page makes the page.
        Then the discount's row shows -50.00 EUR, and the subtotal is 300.00 EUR, the tax 57.00
        EUR, and the total 357.00 EUR."""
        text = self.render(
            [Line("Annual accounts", Decimal("350.00"), 1), Line("Early payment", Decimal("-50.00"), 1)],
            "0.19",
        )

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price        Amount\n"
            + "Annual accounts              1    350.00 EUR    350.00 EUR\n"
            + "Early payment                1    -50.00 EUR    -50.00 EUR\n"
            + "\n"
            + "Subtotal                                        300.00 EUR\n"
            + "Tax 19%                                          57.00 EUR\n"
            + "Total                                           357.00 EUR\n"
        )

    def test_description_longer_than_its_column_wraps_in_its_column(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a line `Annual accounts and the tax return for the year 2025`, longer than the
        Description column of 20, at 350.00.
        When render_page makes the page.
        Then its first row holds `Annual accounts and` with 1, 350.00 EUR, and 350.00 EUR, and
        `the tax return for` and `the year 2025` follow on rows of their own, no word cut."""
        long = "Annual accounts and the tax return for the year 2025"
        text = self.render([Line(long, Decimal("350.00"), 1)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price        Amount\n"
            + "Annual accounts and          1    350.00 EUR    350.00 EUR\n"
            + "the tax return for\n"
            + "the year 2025\n"
            + "\n"
            + "Subtotal                                        350.00 EUR\n"
            + "Tax 19%                                          66.50 EUR\n"
            + "Total                                           416.50 EUR\n"
        )

    def test_description_exactly_as_wide_as_its_column_stays_on_one_line(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a line `Receipts filed 11-01`, 20 characters, exactly as wide as the Description
        column, of 12 at 0.35.
        When render_page makes the page.
        Then the line takes one row alone, with 12, 0.35 EUR, and 4.20 EUR."""
        description = "Receipts filed 11-01"
        self.assertEqual(len(description), page.DESCRIPTION_WIDTH, "the description fills the column")

        text = self.render([Line(description, Decimal("0.35"), 12)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price      Amount\n"
            + "Receipts filed 11-01        12      0.35 EUR    4.20 EUR\n"
            + "\n"
            + "Subtotal                                        4.20 EUR\n"
            + "Tax 19%                                         0.80 EUR\n"
            + "Total                                           5.00 EUR\n"
        )

    def test_word_longer_than_its_column_breaks_at_the_columns_width(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a line `Jahresabschlusserstellung`, one German word of 25 characters, longer than
        the Description column of 20, at 350.00.
        When render_page makes the page.
        Then its first row holds `Jahresabschlusserste` with 1, 350.00 EUR, and 350.00 EUR, and
        the next row holds `llung` alone."""
        text = self.render([Line("Jahresabschlusserstellung", Decimal("350.00"), 1)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price        Amount\n"
            + "Jahresabschlusserste         1    350.00 EUR    350.00 EUR\n"
            + "llung\n"
            + "\n"
            + "Subtotal                                        350.00 EUR\n"
            + "Tax 19%                                          66.50 EUR\n"
            + "Total                                           416.50 EUR\n"
        )

    def test_hyphenated_word_longer_than_its_column_breaks_at_the_columns_width(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a line `Steuerberatung-Jahresabschluss`, one hyphenated German compound of 30
        characters, longer than the Description column of 20, at 350.00.
        When render_page makes the page.
        Then it breaks as any word does, at the column's width: `Steuerberatung-Jahre` with 1,
        350.00 EUR, and 350.00 EUR, and then `sabschluss` alone."""
        text = self.render([Line("Steuerberatung-Jahresabschluss", Decimal("350.00"), 1)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity    Unit price        Amount\n"
            + "Steuerberatung-Jahre         1    350.00 EUR    350.00 EUR\n"
            + "sabschluss\n"
            + "\n"
            + "Subtotal                                        350.00 EUR\n"
            + "Tax 19%                                          66.50 EUR\n"
            + "Total                                           416.50 EUR\n"
        )

    def test_money_columns_widen_to_an_amount_of_many_digits(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given 1000 of a line at 1234567.89, an amount of 1234567890.00, at 19%.
        When render_page makes the page.
        Then the unit price, the amount, the tax 234567899.10 EUR, and the total 1469135789.10 EUR
        show whole, and the header, the line, and the totals rows all end in the same column."""
        text = self.render([Line("Annual accounts", Decimal("1234567.89"), 1000)], "0.19")

        self.assertEqual(
            text,
            HEAD
            + "Description           Quantity        Unit price               Amount\n"
            + "Annual accounts           1000    1234567.89 EUR    1234567890.00 EUR\n"
            + "\n"
            + "Subtotal                                            1234567890.00 EUR\n"
            + "Tax 19%                                              234567899.10 EUR\n"
            + "Total                                               1469135789.10 EUR\n"
        )


if __name__ == "__main__":
    unittest.main()
