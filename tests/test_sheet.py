"""Unit cases of sheet.read_sheet: each class of sheet it reads or refuses."""

import os
import shutil
import tempfile
import unittest
import zipfile
from decimal import Decimal

from invoicer import sheet
from invoicer.lines import Line
from tests import helpers


class SheetCase(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)

    def write(self, rows, name="nordwind-2026-11.ods", more_sheets=()):
        return helpers.write_ods(os.path.join(self.folder, name), rows, more_sheets)

    def read(self, rows, **kwargs):
        read = sheet.read_sheet(self.write(rows, **kwargs))
        self.assertIsInstance(read, tuple)
        return read

    def read_lines(self, rows):
        _, lines = self.read(rows)
        return [(line.description, line.price, line.quantity) for line in lines]

    def assertRefuses(self, path, message):
        with self.assertRaises(sheet.SheetError) as refused:
            sheet.read_sheet(path)
        self.assertEqual(str(refused.exception), message)


def rewrite(path, old, new):
    """Rewrites the content.xml of the .ods file at path with its one old text as new, as Calc
    saves a cell in a way that write_ods doesn't."""
    with zipfile.ZipFile(path) as ods:
        xml = ods.read("content.xml").decode("utf-8")
    if xml.count(old) != 1:
        raise ValueError(f"content.xml holds {old!r} {xml.count(old)} times, not once")
    with zipfile.ZipFile(path, "w") as ods:
        ods.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        ods.writestr("META-INF/manifest.xml", helpers.MANIFEST)
        ods.writestr("content.xml", xml.replace(old, new))


def with_cell(row, column, value, rows=None):
    rows = helpers.nordwind_rows() if rows is None else rows
    rows[row - 1][column] = value
    return rows


NORDWIND = [
    ("Bookkeeping hours", Decimal("80.00"), 10),
    ("Annual accounts", Decimal("350.00"), 1),
    ("Travel to client", Decimal("25.50"), 2),
]


class ReadsTheSheet(SheetCase):
    def test_details_come_from_the_labels_in_column_a(self):
        """Supports: PrintsTheInvoice.test_page_the_printer_gets_is_made_from_the_sheets_details_lines_and_rate

        Given the Nordwind sheet.
        When read_sheet reads it.
        Then the Details hold each value of column B under its label of column A, as text."""
        details, _ = self.read(helpers.nordwind_rows())

        self.assertEqual(
            details,
            sheet.Details(
                invoice_number="2026-041",
                date="2026-11-19",
                client_name="Nordwind Handel GmbH",
                client_address="Hafenweg 12, 20457 Hamburg",
                our_name="Lindqvist Buchhaltung GmbH",
                our_address="Hauptstraße 5, 10115 Berlin",
                our_vat_id="DE123456789",
            ),
        )

    def test_date_cell_gives_the_date_as_year_month_day(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the Nordwind sheet, whose `Date` Calc keeps as a date cell of 2026-11-19 shown as
        `19.11.26`.
        When read_sheet reads it.
        Then the date is `2026-11-19`."""
        path = self.write(helpers.nordwind_rows())
        with zipfile.ZipFile(path) as ods:
            xml = ods.read("content.xml").decode("utf-8")
        xml = xml.replace("<text:p>2026-11-19</text:p>", "<text:p>19.11.26</text:p>")
        self.assertIn("19.11.26", xml)
        os.remove(path)
        with zipfile.ZipFile(path, "w") as ods:
            ods.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
            ods.writestr("META-INF/manifest.xml", helpers.MANIFEST)
            ods.writestr("content.xml", xml)

        read = sheet.read_sheet(path)

        self.assertIsInstance(read, tuple)
        self.assertEqual(read[0].date, "2026-11-19")

    def test_row_above_the_header_without_a_label_is_passed_over(self):
        """Supports: PrintsTheInvoice.test_page_the_printer_gets_is_made_from_the_sheets_details_lines_and_rate

        Given the Nordwind sheet with a title row `Rechnung` before its details, and a note in
        column B alone between two detail rows.
        When read_sheet reads it.
        Then the Details are the guide's, each read by its label, the title and the note left
        out."""
        rows = helpers.nordwind_rows()
        rows[3:3] = [[None, "see contract 2025-7"]]
        rows[0:0] = [["Rechnung"]]

        details, _ = self.read(rows)

        self.assertEqual(
            details,
            sheet.Details(
                invoice_number="2026-041",
                date="2026-11-19",
                client_name="Nordwind Handel GmbH",
                client_address="Hafenweg 12, 20457 Hamburg",
                our_name="Lindqvist Buchhaltung GmbH",
                our_address="Hauptstraße 5, 10115 Berlin",
                our_vat_id="DE123456789",
            ),
        )

    def test_date_cell_holding_a_time_gives_the_date_alone(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the Nordwind sheet whose `Date` is a date cell Calc keeps with a time,
        2026-11-19T09:30:00.
        When read_sheet reads it.
        Then the date is `2026-11-19`."""
        path = self.write(helpers.nordwind_rows())
        rewrite(path, 'office:date-value="2026-11-19"', 'office:date-value="2026-11-19T09:30:00"')

        details, _ = sheet.read_sheet(path)

        self.assertEqual(details.date, "2026-11-19")

    def test_number_cell_detail_is_read_as_its_text(self):
        """Supports: PrintsTheInvoice.test_message_names_the_sheets_invoice_number_and_client

        Given a sheet whose `Invoice number` is the number cell 42.
        When read_sheet reads it.
        Then the invoice number is the text `42`."""
        details, _ = self.read(with_cell(1, 1, 42))

        self.assertEqual(details.invoice_number, "42")

    def test_lines_come_from_the_rows_under_the_header(self):
        """Supports: PrintsTheInvoice.test_page_the_printer_gets_is_made_from_the_sheets_details_lines_and_rate

        Given the Nordwind sheet.
        When read_sheet reads it.
        Then its lines are Lines of each row's description, exact Decimal price, and exact
        quantity, never a float."""
        _, lines = self.read(helpers.nordwind_rows())

        self.assertTrue(all(isinstance(line, Line) for line in lines))
        self.assertEqual([(l.description, l.price, l.quantity) for l in lines], NORDWIND)
        self.assertTrue(all(isinstance(l.price, Decimal) for l in lines))
        self.assertTrue(all(isinstance(l.quantity, (int, Decimal)) for l in lines))

    def test_header_columns_in_any_order(self):
        """Supports: PrintsTheInvoice.test_header_in_any_column_order_bills_the_same_lines

        Given a sheet whose header reads `Price`, `Quantity`, `Description`.
        When read_sheet reads it.
        Then each line takes its description, price, and quantity from the column under its
        header."""
        lines = [[price, quantity, description] for description, price, quantity in helpers.NORDWIND_LINES]
        rows = helpers.nordwind_rows(lines=lines, header=["Price", "Quantity", "Description"])

        self.assertEqual(self.read_lines(rows), NORDWIND)

    def test_header_with_several_empty_columns_between(self):
        """Supports: PrintsTheInvoice.test_header_in_any_column_order_bills_the_same_lines

        Given a sheet whose header has `Description` in A, `Price` in D, and `Quantity` in G,
        the empty columns between them written by Calc as one repeated cell each.
        When read_sheet reads it.
        Then each line takes its price from D and its quantity from G."""
        lines = [
            [description, None, None, price, None, None, quantity]
            for description, price, quantity in helpers.NORDWIND_LINES
        ]
        header = ["Description", None, None, "Price", None, None, "Quantity"]

        self.assertEqual(self.read_lines(helpers.nordwind_rows(lines=lines, header=header)), NORDWIND)

    def test_cells_calc_saves_as_repeated_fill_each_column(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose line in row 11 is a stamp at 1 of quantity 1, the two equal cells of
        Price and Quantity side by side, which Calc saves as one cell repeated twice.
        When read_sheet reads it.
        Then the line's price and quantity are each 1."""
        lines = [list(line) for line in helpers.NORDWIND_LINES]
        lines[1] = ["Stamp", 1, 1]
        path = self.write(helpers.nordwind_rows(lines=lines))
        one = '<table:table-cell office:value-type="float" office:value="1"><text:p>1</text:p></table:table-cell>'
        rewrite(path, one + one, one.replace('office:value="1"', 'office:value="1" table:number-columns-repeated="2"'))

        _, read = sheet.read_sheet(path)

        self.assertEqual(
            [(l.description, l.price, l.quantity) for l in read],
            [NORDWIND[0], ("Stamp", Decimal("1"), 1), NORDWIND[2]],
        )

    def test_header_with_an_empty_column_between(self):
        """Supports: PrintsTheInvoice.test_header_in_any_column_order_bills_the_same_lines

        Given a sheet whose header has `Description` in A, nothing in B, and `Price` and
        `Quantity` in C and D, which Calc writes as a repeated empty cell.
        When read_sheet reads it.
        Then each line takes its cells from C and D, past the empty column."""
        lines = [[description, None, price, quantity] for description, price, quantity in helpers.NORDWIND_LINES]
        rows = helpers.nordwind_rows(lines=lines, header=["Description", None, "Price", "Quantity"])

        self.assertEqual(self.read_lines(rows), NORDWIND)

    def test_label_with_spaces_around_it_is_found(self):
        """Supports: PrintsTheInvoice.test_page_the_printer_gets_is_made_from_the_sheets_details_lines_and_rate

        Given the Nordwind sheet whose label in row 3 is typed ` Client name ` with a space before
        and after it.
        When read_sheet reads it.
        Then the client name is read under that label, as if typed `Client name`."""
        details, _ = self.read(with_cell(3, 0, " Client name "))

        self.assertEqual(details.client_name, "Nordwind Handel GmbH")

    def test_header_names_with_spaces_around_them_are_found(self):
        """Supports: PrintsTheInvoice.test_header_in_any_column_order_bills_the_same_lines

        Given the Nordwind sheet whose header row 9 reads ` Description`, `Price `, and
        ` Quantity `, with spaces around the names.
        When read_sheet reads it.
        Then each line takes its cells from the columns under those names, as if typed without
        the spaces."""
        rows = helpers.nordwind_rows(header=[" Description", "Price ", " Quantity "])

        self.assertEqual(self.read_lines(rows), NORDWIND)

    def test_price_in_a_number_cell_that_shows_no_text_is_read_by_its_value(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given the Nordwind sheet whose price in row 11 is a number cell that Calc stores as 350
        but saves with no text shown, as a format that hides the figure does.
        When read_sheet reads it.
        Then the line's price is Decimal 350, not refused as empty."""
        path = self.write(helpers.nordwind_rows())
        rewrite(
            path,
            '<table:table-cell office:value-type="float" office:value="350"><text:p>350.00</text:p>'
            "</table:table-cell>",
            '<table:table-cell office:value-type="float" office:value="350"/>',
        )

        _, lines = sheet.read_sheet(path)

        self.assertEqual(
            [(l.description, l.price, l.quantity) for l in lines],
            [NORDWIND[0], ("Annual accounts", Decimal("350"), 1), NORDWIND[2]],
        )

    def test_quantity_in_a_number_cell_that_shows_no_text_is_read_by_its_value(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given the Nordwind sheet whose quantity in row 10 is a number cell that Calc stores as 10
        but saves with no text shown.
        When read_sheet reads it.
        Then the line's quantity is the int 10, not refused as empty."""
        path = self.write(helpers.nordwind_rows())
        rewrite(
            path,
            '<table:table-cell office:value-type="float" office:value="10"><text:p>10</text:p>'
            "</table:table-cell>",
            '<table:table-cell office:value-type="float" office:value="10"/>',
        )

        _, lines = sheet.read_sheet(path)

        self.assertEqual([(l.description, l.price, l.quantity) for l in lines], NORDWIND)

    def test_one_line(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given a sheet with a single line under its header.
        When read_sheet reads it.
        Then it gives that one line."""
        rows = helpers.nordwind_rows(lines=[helpers.NORDWIND_LINES[0]])

        self.assertEqual(self.read_lines(rows), NORDWIND[:1])

    def test_only_the_first_sheet(self):
        """Supports: PrintsTheInvoice.test_only_the_first_sheet_is_read

        Given a file whose first sheet is Nordwind's and whose second holds another table.
        When read_sheet reads it.
        Then the lines are the first sheet's."""
        _, lines = self.read(
            helpers.nordwind_rows(), more_sheets=[[["Description", "Price", "Quantity"], ["Other", 1, 1]]]
        )

        self.assertEqual([(l.description, l.price, l.quantity) for l in lines], NORDWIND)

    def test_date_typed_as_text_is_kept_as_typed(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose `Date` is typed as German accounting writes it, day first with points
        between, so that Calc kept it as text.
        When read_sheet reads it.
        Then the date is that text, as typed."""
        details, _ = self.read(with_cell(2, 1, "19.11.2026"))

        self.assertEqual(details.date, "19.11.2026")

    def test_price_kept_as_text_of_a_number_is_taken(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose price in row 10 is the text cell `80.00`, as a pasted value lands.
        When read_sheet reads it.
        Then the line's price is Decimal 80.00."""
        lines = self.read_lines(with_cell(10, 1, "80.00"))

        self.assertEqual(lines[0], ("Bookkeeping hours", Decimal("80.00"), 10))

    def test_price_as_text_with_a_decimal_comma_is_taken(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose price in row 10 is the text cell `80,00`, as German accounting pastes
        it.
        When read_sheet reads it.
        Then the line's price is Decimal 80.00."""
        lines = self.read_lines(with_cell(10, 1, "80,00"))

        self.assertEqual(lines[0], ("Bookkeeping hours", Decimal("80.00"), 10))

    def test_price_of_many_digits_is_read_exactly(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose price in row 11 is the number cell 1234567.89.
        When read_sheet reads it.
        Then the line's price is exactly Decimal 1234567.89."""
        lines = self.read_lines(with_cell(11, 1, Decimal("1234567.89")))

        self.assertEqual(lines[1], ("Annual accounts", Decimal("1234567.89"), 1))

    def test_price_a_formula_gives_past_the_cent_is_read_exactly(self):
        """Supports: MoneyToTheCent.test_amounts_are_rounded_to_the_cent_and_the_page_adds_up

        Given a sheet whose price in row 11 is a number cell that a formula gave as
        400.333333333333, which Calc shows as 400.33.
        When read_sheet reads it.
        Then the line's price is exactly Decimal 400.333333333333, left for the page to round."""
        lines = self.read_lines(with_cell(11, 1, Decimal("400.333333333333")))

        self.assertEqual(lines[1], ("Annual accounts", Decimal("400.333333333333"), 1))

    def test_price_in_a_currency_cell_is_read_by_its_stored_value(self):
        """Supports: PrintsTheInvoice.test_price_in_a_currency_cell_bills_its_value

        Given a sheet whose price in row 10 is a Currency cell, which Calc shows as `80,00 €` and
        stores as 80.
        When read_sheet reads it.
        Then the line's price is Decimal 80."""
        lines = self.read_lines(with_cell(10, 1, ("currency", "80", "80,00 €")))

        self.assertEqual(lines[0], ("Bookkeeping hours", Decimal("80"), 10))

    def test_quantity_in_a_percent_cell_is_read_by_its_stored_value(self):
        """Supports: PrintsTheInvoice.test_price_in_a_currency_cell_bills_its_value

        Given a sheet whose quantity in row 11 is a Percent cell, which Calc shows as `50%` and
        stores as 0.5.
        When read_sheet reads it.
        Then the line's quantity is Decimal 0.5."""
        lines = self.read_lines(with_cell(11, 2, ("percentage", "0.5", "50%")))

        self.assertEqual(lines[1], ("Annual accounts", Decimal("350.00"), Decimal("0.5")))

    def test_whole_quantity_is_an_int(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the Nordwind sheet, whose quantity in row 10 is the number cell 10.
        When read_sheet reads it.
        Then the line's quantity is the int 10, not a Decimal."""
        lines = self.read_lines(helpers.nordwind_rows())

        self.assertIs(type(lines[0][2]), int)
        self.assertEqual(lines[0][2], 10)

    def test_whole_quantity_typed_with_a_decimal_comma_is_an_int(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given a sheet whose quantity in row 12 is the text cell `2,0`.
        When read_sheet reads it.
        Then the line's quantity is the int 2."""
        lines = self.read_lines(with_cell(12, 2, "2,0"))

        self.assertIs(type(lines[2][2]), int)
        self.assertEqual(lines[2][2], 2)

    def test_price_of_zero_is_taken(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose line in row 11 is a free first consultation at the price 0.
        When read_sheet reads it.
        Then the line's price is 0."""
        lines = self.read_lines(with_cell(11, 1, Decimal("0")))

        self.assertEqual(lines[1], ("Annual accounts", Decimal("0"), 1))

    def test_negative_price_is_taken_as_a_discount(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose line in row 12 is a discount at the price -50.00.
        When read_sheet reads it.
        Then the line's price is Decimal -50.00."""
        lines = self.read_lines(with_cell(12, 1, Decimal("-50.00")))

        self.assertEqual(lines[2], ("Travel to client", Decimal("-50.00"), 2))

    def test_quantity_of_hours_with_a_half_is_taken(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose quantity in row 10 is the number cell 2.5, two and a half hours.
        When read_sheet reads it.
        Then the line's quantity is exactly Decimal 2.5."""
        lines = self.read_lines(with_cell(10, 2, Decimal("2.5")))

        self.assertEqual(lines[0], ("Bookkeeping hours", Decimal("80.00"), Decimal("2.5")))
        self.assertIsInstance(lines[0][2], Decimal)

    def test_quantity_as_text_with_a_decimal_comma_is_taken(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose quantity in row 10 is the text cell `2,5`.
        When read_sheet reads it.
        Then the line's quantity is Decimal 2.5."""
        lines = self.read_lines(with_cell(10, 2, "2,5"))

        self.assertEqual(lines[0], ("Bookkeeping hours", Decimal("80.00"), Decimal("2.5")))

    def test_quantity_just_more_than_zero_is_taken(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet whose quantity in row 10 is 0.01, the least more than 0 that a cell of
        cents holds.
        When read_sheet reads it.
        Then the line's quantity is Decimal 0.01."""
        lines = self.read_lines(with_cell(10, 2, Decimal("0.01")))

        self.assertEqual(lines[0], ("Bookkeeping hours", Decimal("80.00"), Decimal("0.01")))

    def test_description_longer_than_the_pages_column_is_read_whole(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose description in row 11 is `Annual accounts and the tax return for the
        year 2025`, longer than the page's Description column.
        When read_sheet reads it.
        Then the line's description is that text, whole."""
        long = "Annual accounts and the tax return for the year 2025"
        lines = self.read_lines(with_cell(11, 0, long))

        self.assertEqual(lines[1], (long, Decimal("350.00"), 1))

    def test_description_with_spaces_around_it_is_billed_without_them(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given a sheet whose description in row 11 is `  Annual accounts  `, typed with spaces
        before and after it.
        When read_sheet reads it.
        Then the line's description is `Annual accounts`, without the spaces."""
        lines = self.read_lines(with_cell(11, 0, "  Annual accounts  "))

        self.assertEqual(lines[1], ("Annual accounts", Decimal("350.00"), 1))

    def test_first_row_naming_a_header_name_is_the_header(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given the Nordwind sheet with a fourth line in row 13 whose description is `Price`, one
        of the header's names, at 10.00 once.
        When read_sheet reads it.
        Then the header is row 9, the first row naming a header name, and the lines are the
        four under it, the last one `Price`."""
        typed_lines = helpers.NORDWIND_LINES + [["Price", Decimal("10.00"), 1]]
        rows = helpers.nordwind_rows(lines=typed_lines)

        lines = self.read_lines(rows)

        self.assertEqual(lines, NORDWIND + [("Price", Decimal("10.00"), 1)])

    def test_header_right_under_the_last_detail(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given the Nordwind sheet with no empty row between its details and its header, so the
        header is row 8, right under the seller's VAT ID in row 7.
        When read_sheet reads it.
        Then the details are Nordwind's and the lines are the three under the header."""
        rows = helpers.nordwind_rows()
        del rows[7]

        details, lines = self.read(rows)

        self.assertEqual(details.our_vat_id, "DE123456789")
        self.assertEqual([(l.description, l.price, l.quantity) for l in lines], NORDWIND)

    def test_header_after_several_empty_rows(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given the Nordwind sheet with three empty rows between its details and its header, which
        Calc writes as one repeated row.
        When read_sheet reads it.
        Then the details are Nordwind's and the lines are the three under the header."""
        rows = helpers.nordwind_rows()
        rows[7:7] = [[], []]

        details, lines = self.read(rows)

        self.assertEqual(details.our_vat_id, "DE123456789")
        self.assertEqual([(l.description, l.price, l.quantity) for l in lines], NORDWIND)

    def test_empty_rows_between_detail_rows(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given the Nordwind sheet with an empty row between `Client name` and `Client address`,
        and two between `Client address` and the seller's name.
        When read_sheet reads it.
        Then the Details hold each label's value as in the guide's sheet."""
        rows = helpers.nordwind_rows()
        rows[4:4] = [[], []]
        rows[3:3] = [[]]

        details, _ = self.read(rows)

        self.assertEqual(
            details,
            sheet.Details(
                invoice_number="2026-041",
                date="2026-11-19",
                client_name="Nordwind Handel GmbH",
                client_address="Hafenweg 12, 20457 Hamburg",
                our_name="Lindqvist Buchhaltung GmbH",
                our_address="Hauptstraße 5, 10115 Berlin",
                our_vat_id="DE123456789",
            ),
        )

    def test_row_calc_saves_as_repeated_bills_each_copy(self):
        """Supports: PrintsTheInvoice.test_lines_as_accounting_keeps_them_bill_right

        Given the Nordwind sheet whose travel line, row 12, was copied down into rows 13 and 14,
        which Calc saves as one row repeated 3 times.
        When read_sheet reads it.
        Then its lines are the first two and the travel line three times."""
        path = helpers.repeat_row(self.write(helpers.nordwind_rows()), "Travel to client", 3)

        _, lines = sheet.read_sheet(path)

        self.assertEqual(
            [(l.description, l.price, l.quantity) for l in lines],
            NORDWIND + [("Travel to client", Decimal("25.50"), 2)] * 2,
        )


class RefusesTheSheet(SheetCase):
    def write_zip(self, name, files):
        """Writes a zip file named name in the test's folder, holding files, a dict of each
        name to its text."""
        path = os.path.join(self.folder, name)
        with zipfile.ZipFile(path, "w") as other:
            for each, text in files.items():
                other.writestr(each, text)
        return path

    def test_missing_file(self):
        """Supports: RefusesWhatIsWrong.test_missing_file_is_refused

        Given no file at the path.
        When read_sheet reads it.
        Then it refuses, naming the file and saying to check its name and folder."""
        path = os.path.join(self.folder, "missing.ods")

        self.assertRefuses(path, f"{path}: there's no such file: check the sheet's name and folder")

    def test_folder(self):
        """Supports: RefusesWhatIsWrong.test_folder_is_refused

        Given the path of a folder, where the colleague gave the folder of the sheet.
        When read_sheet reads it.
        Then it refuses with `<path> is a folder; give the .ods file inside it`."""
        self.assertRefuses(self.folder, f"{self.folder} is a folder; give the .ods file inside it")

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root may read any file")
    def test_file_it_may_not_read(self):
        """Supports: RefusesWhatIsWrong.test_sheet_it_may_not_read_is_refused

        Given the Nordwind sheet saved with no permission for anyone to read it.
        When read_sheet reads it.
        Then it refuses, naming the file, saying invoicer may not read it, and to ask whoever
        shared it for access."""
        path = self.write(helpers.nordwind_rows())
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)

        self.assertRefuses(
            path,
            f"{path} can't be opened: you may not read it. Ask whoever shared it to give you access.",
        )

    def test_text_file(self):
        """Supports: RefusesWhatIsWrong.test_file_that_isnt_an_ods_is_refused

        Given a .csv text file.
        When read_sheet reads it.
        Then it refuses, naming the file and saying to save it as an .ods."""
        path = os.path.join(self.folder, "lines.csv")
        with open(path, "w", encoding="utf-8") as csv:
            csv.write("Description,Price,Quantity\n")

        self.assertRefuses(
            path, f"{path} isn't an .ods spreadsheet: save the sheet in Calc as ODF Spreadsheet (.ods)"
        )

    def test_zip_that_isnt_a_spreadsheet(self):
        """Supports: RefusesWhatIsWrong.test_file_that_isnt_an_ods_is_refused

        Given a zip file named `.ods` that holds neither mimetype nor content.xml.
        When read_sheet reads it.
        Then it refuses, saying it isn't an .ods spreadsheet."""
        path = self.write_zip("other.ods", {"notes.txt": "hello"})

        self.assertRefuses(
            path, f"{path} isn't an .ods spreadsheet: save the sheet in Calc as ODF Spreadsheet (.ods)"
        )

    def test_ods_that_holds_a_text_document(self):
        """Supports: RefusesWhatIsWrong.test_file_that_isnt_an_ods_is_refused

        Given a Writer text document renamed `.ods`, holding the mimetype of a text document and
        a content.xml whose table holds the Nordwind lines.
        When read_sheet reads it.
        Then it refuses, saying it isn't an .ods spreadsheet."""
        with zipfile.ZipFile(self.write(helpers.nordwind_rows())) as ods:
            content = ods.read("content.xml").decode("utf-8")
        path = self.write_zip(
            "letter.ods", {"mimetype": "application/vnd.oasis.opendocument.text", "content.xml": content}
        )

        self.assertRefuses(
            path, f"{path} isn't an .ods spreadsheet: save the sheet in Calc as ODF Spreadsheet (.ods)"
        )

    def test_ods_that_holds_no_spreadsheet(self):
        """Supports: RefusesWhatIsWrong.test_file_that_isnt_an_ods_is_refused

        Given an .ods file with the mimetype of a spreadsheet whose content.xml holds no sheet.
        When read_sheet reads it.
        Then it refuses, saying it isn't an .ods spreadsheet."""
        path = self.write_zip(
            "empty.ods",
            {
                "mimetype": "application/vnd.oasis.opendocument.spreadsheet",
                "content.xml": helpers.CONTENT.format(tables=""),
            },
        )

        self.assertRefuses(
            path, f"{path} isn't an .ods spreadsheet: save the sheet in Calc as ODF Spreadsheet (.ods)"
        )

    def test_ods_whose_content_isnt_xml(self):
        """Supports: RefusesWhatIsWrong.test_file_that_isnt_an_ods_is_refused

        Given an .ods file with the mimetype of a spreadsheet whose content.xml is cut short.
        When read_sheet reads it.
        Then it refuses, saying it isn't an .ods spreadsheet."""
        path = self.write_zip(
            "broken.ods",
            {
                "mimetype": "application/vnd.oasis.opendocument.spreadsheet",
                "content.xml": "<office:document-content",
            },
        )

        self.assertRefuses(
            path, f"{path} isn't an .ods spreadsheet: save the sheet in Calc as ODF Spreadsheet (.ods)"
        )

    def test_missing_label(self):
        """Supports: RefusesWhatIsWrong.test_missing_label_is_refused

        Given a sheet without its `Client address` row.
        When read_sheet reads it.
        Then it refuses, naming `Client address` and where to put it."""
        details = [row for row in helpers.NORDWIND_DETAILS if row[0] != "Client address"]

        self.assertRefuses(
            self.write(helpers.nordwind_rows(details=details)),
            "the `Client address` row is missing: put `Client address` in column A of a row above "
            "the header and its value in column B",
        )

    def test_label_given_twice(self):
        """Supports: RefusesWhatIsWrong.test_label_given_twice_is_refused_naming_both_rows

        Given a sheet whose `Invoice number` stands in row 1 with 2026-041 and again in row 2 with
        2026-040, left from the last invoice.
        When read_sheet reads it.
        Then it refuses, naming rows 1 and 2."""
        details = [list(row) for row in helpers.NORDWIND_DETAILS]
        details.insert(1, ["Invoice number", "2026-040"])

        self.assertRefuses(
            self.write(helpers.nordwind_rows(details=details)),
            "rows 1 and 2 both hold the label `Invoice number`: keep the row with this invoice's "
            "value and delete the other",
        )

    def test_label_with_an_empty_value(self):
        """Supports: RefusesWhatIsWrong.test_label_with_an_empty_value_is_refused_naming_its_row

        Given a sheet whose `Client name` label stands in row 3 with nothing in column B.
        When read_sheet reads it.
        Then it refuses with `row 3: the Client name is empty`."""
        self.assertRefuses(self.write(with_cell(3, 1, None)), "row 3: the Client name is empty")

    def test_label_with_a_value_of_only_spaces(self):
        """Supports: RefusesWhatIsWrong.test_label_with_an_empty_value_is_refused_naming_its_row

        Given a sheet whose seller's VAT ID in row 7 is a text cell of spaces alone.
        When read_sheet reads it.
        Then it refuses, naming row 7 and the seller's VAT ID as empty."""
        self.assertRefuses(self.write(with_cell(7, 1, "   ")), "row 7: the Our VAT ID is empty")

    def test_missing_header(self):
        """Supports: RefusesWhatIsWrong.test_missing_header_is_refused

        Given a sheet whose header row 9 names `Description` and `Quantity` but no `Price`.
        When read_sheet reads it.
        Then it refuses, naming row 9 and the Price column."""
        rows = helpers.nordwind_rows(header=["Description", "Cost", "Quantity"])

        self.assertRefuses(
            self.write(rows),
            "row 9: the header has no Price column: name its column Price, as Description, Price, "
            "and Quantity",
        )

    def test_header_naming_a_column_twice(self):
        """Supports: RefusesWhatIsWrong.test_missing_header_is_refused

        Given a sheet whose header row 9 names `Price` in column B and again in column D.
        When read_sheet reads it.
        Then it refuses, naming row 9, Price, and columns B and D."""
        lines = [list(line) + [Decimal("1.00")] for line in helpers.NORDWIND_LINES]
        rows = helpers.nordwind_rows(lines=lines, header=["Description", "Price", "Quantity", "Price"])

        self.assertRefuses(
            self.write(rows),
            "row 9: the header names Price twice, in columns B and D: rename or clear one of them",
        )

    def test_header_naming_a_column_twice_in_column_z(self):
        """Supports: RefusesWhatIsWrong.test_missing_header_is_refused

        Given a sheet whose header row 9 names `Price` in column B and again in column Z, the
        last column of one letter.
        When read_sheet reads it.
        Then it refuses, naming row 9, Price, and columns B and Z."""
        rows = helpers.nordwind_rows(header=["Description", "Price", "Quantity"] + [None] * 22 + ["Price"])

        self.assertRefuses(
            self.write(rows),
            "row 9: the header names Price twice, in columns B and Z: rename or clear one of them",
        )

    def test_header_naming_a_column_twice_past_column_z(self):
        """Supports: RefusesWhatIsWrong.test_missing_header_is_refused

        Given a sheet whose header row 9 names `Price` in column B and again in column AA, the
        first column of two letters, past Z.
        When read_sheet reads it.
        Then it refuses, naming row 9, Price, and columns B and AA, as Calc names them."""
        rows = helpers.nordwind_rows(header=["Description", "Price", "Quantity"] + [None] * 23 + ["Price"])

        self.assertRefuses(
            self.write(rows),
            "row 9: the header names Price twice, in columns B and AA: rename or clear one of them",
        )

    def test_no_header_row(self):
        """Supports: RefusesWhatIsWrong.test_missing_header_is_refused

        Given a sheet whose row under the details names `Item`, `Cost`, and `Count`, none of the
        header's names.
        When read_sheet reads it.
        Then it refuses, saying to put a row naming Description, Price, and Quantity."""
        rows = helpers.nordwind_rows(header=["Item", "Cost", "Count"])

        self.assertRefuses(
            self.write(rows),
            "the sheet has no header row: put a row naming Description, Price, and Quantity below "
            "the details",
        )

    def test_empty_description(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet whose line in row 10 has a price and quantity but no description.
        When read_sheet reads it.
        Then it refuses with `row 10: the description is empty`."""
        self.assertRefuses(self.write(with_cell(10, 0, None)), "row 10: the description is empty")

    def test_description_of_only_spaces(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet whose description in row 10 is three spaces, with its price and quantity.
        When read_sheet reads it.
        Then it refuses with `row 10: the description is empty`."""
        self.assertRefuses(self.write(with_cell(10, 0, "   ")), "row 10: the description is empty")

    def test_empty_price(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet whose line in row 11 has no price.
        When read_sheet reads it.
        Then it refuses with `row 11: the price is empty`."""
        self.assertRefuses(self.write(with_cell(11, 1, None)), "row 11: the price is empty")

    def test_price_not_a_number(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet whose price in row 12 is the text `twenty`.
        When read_sheet reads it.
        Then it refuses, naming row 12 and `twenty`, and saying to type a number."""
        self.assertRefuses(
            self.write(with_cell(12, 1, "twenty")),
            "row 12: the price `twenty` isn't a number: type it as a number, such as 80.00",
        )

    def test_price_with_a_plus_sign(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet whose price in row 10 is the text `+80`, a form no case names.
        When read_sheet reads it.
        Then it refuses, naming row 10 and `+80`."""
        self.assertRefuses(
            self.write(with_cell(10, 1, "+80")),
            "row 10: the price `+80` isn't a number: type it as a number, such as 80.00",
        )

    def test_price_as_text_with_a_point_before_three_digits(self):
        """Supports: RefusesWhatIsWrong.test_price_that_reads_two_ways_is_refused

        Given a sheet whose price in row 10 is the text `1.200`, which German accounting writes
        for twelve hundred and Python reads as 1.2.
        When read_sheet reads it.
        Then it refuses with `row 10: write the price as a plain number, such as 1200.00`."""
        self.assertRefuses(
            self.write(with_cell(10, 1, "1.200")),
            "row 10: write the price as a plain number, such as 1200.00",
        )

    def test_price_as_text_with_a_comma_before_three_digits(self):
        """Supports: RefusesWhatIsWrong.test_price_that_reads_two_ways_is_refused

        Given a sheet whose price in row 11 is the text `1,200`, which English writes for twelve
        hundred and German for 1.2.
        When read_sheet reads it.
        Then it refuses with `row 11: write the price as a plain number, such as 1200.00`."""
        self.assertRefuses(
            self.write(with_cell(11, 1, "1,200")),
            "row 11: write the price as a plain number, such as 1200.00",
        )

    def test_price_as_text_with_a_thousands_point_and_a_decimal_comma(self):
        """Supports: RefusesWhatIsWrong.test_price_that_reads_two_ways_is_refused

        Given a sheet whose price in row 12 is the text `1.200,00`, with two marks.
        When read_sheet reads it.
        Then it refuses with `row 12: write the price as a plain number, such as 1200.00`."""
        self.assertRefuses(
            self.write(with_cell(12, 1, "1.200,00")),
            "row 12: write the price as a plain number, such as 1200.00",
        )

    def test_empty_quantity(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet whose line in row 10 has no quantity.
        When read_sheet reads it.
        Then it refuses with `row 10: the quantity is empty`."""
        self.assertRefuses(self.write(with_cell(10, 2, None)), "row 10: the quantity is empty")

    def test_quantity_not_a_number(self):
        """Supports: RefusesWhatIsWrong.test_wrong_last_line_stops_the_whole_invoice

        Given a sheet whose quantity in row 12 is the text `two`.
        When read_sheet reads it.
        Then it refuses, naming row 12 and `two`, and saying to type how many as a number."""
        self.assertRefuses(
            self.write(with_cell(12, 2, "two")),
            "row 12: the quantity `two` isn't a number: type how many as a number, such as 10",
        )

    def test_quantity_zero(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet whose quantity in row 10 is 0, the highest refused.
        When read_sheet reads it.
        Then it refuses with `row 10: the quantity is 0: type how many, more than 0`."""
        self.assertRefuses(
            self.write(with_cell(10, 2, 0)), "row 10: the quantity is 0: type how many, more than 0"
        )

    def test_quantity_below_zero(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet whose quantity in row 11 is -1.
        When read_sheet reads it.
        Then it refuses with `row 11: the quantity is -1: type how many, more than 0`."""
        self.assertRefuses(
            self.write(with_cell(11, 2, -1)), "row 11: the quantity is -1: type how many, more than 0"
        )

    def test_no_lines(self):
        """Supports: RefusesWhatIsWrong.test_sheet_with_no_lines_is_refused

        Given a sheet with its header row 9 and nothing under it.
        When read_sheet reads it.
        Then it refuses, saying it has no lines and to put them under the header in row 9."""
        self.assertRefuses(
            self.write(helpers.nordwind_rows(lines=[])),
            "the sheet has no lines: put each line in the rows right under the header in row 9",
        )

    def test_line_below_an_empty_row(self):
        """Supports: RefusesWhatIsWrong.test_line_below_an_empty_row_is_refused_naming_both_rows

        Given the Nordwind sheet with row 13 empty and a postage line in row 14 under it.
        When read_sheet reads it.
        Then it refuses, naming row 14 and the empty row 13, as leaving the line off would make
        the total too low."""
        rows = helpers.nordwind_rows() + [[], ["Postage", Decimal("1.00"), 1]]

        self.assertRefuses(
            self.write(rows),
            "row 14 holds text below the empty row 13, where the lines end: delete the empty row "
            "13 to bill row 14, or clear row 14",
        )

    def test_note_several_empty_rows_below_the_lines(self):
        """Supports: RefusesWhatIsWrong.test_line_below_an_empty_row_is_refused_naming_both_rows

        Given the Nordwind sheet with rows 13 to 15 empty, which Calc writes as one repeated row,
        and the note `Paid by transfer` in row 16.
        When read_sheet reads it.
        Then it refuses, naming row 16 and the empty row 13."""
        rows = helpers.nordwind_rows() + [[], [], [], ["Paid by transfer"]]

        self.assertRefuses(
            self.write(rows),
            "row 16 holds text below the empty row 13, where the lines end: delete the empty row "
            "13 to bill row 16, or clear row 16",
        )

    def test_row_numbers_count_the_empty_rows_calc_repeats(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given a sheet with two empty rows between its details and its header, which Calc writes
        as one repeated row, so the header is row 10 and the lines rows 11 to 13.
        When its line in row 12 has no price.
        Then it refuses with `row 12: the price is empty`."""
        rows = helpers.nordwind_rows()
        rows.insert(7, [])
        rows[11][1] = None

        self.assertRefuses(self.write(rows), "row 12: the price is empty")

    def test_row_calc_saves_as_repeated_gives_each_copy_its_own_row_number(self):
        """Supports: RefusesWhatIsWrong.test_wrong_cell_is_refused_naming_its_row

        Given the Nordwind sheet whose travel line, row 12, was copied down into row 13, which
        Calc saves as one row repeated twice, and whose next line, now row 14, has no price.
        When read_sheet reads it.
        Then it refuses with `row 14: the price is empty`."""
        rows = helpers.nordwind_rows(lines=helpers.NORDWIND_LINES + [["Postage", None, 1]])
        path = helpers.repeat_row(self.write(rows), "Travel to client", 2)

        self.assertRefuses(path, "row 14: the price is empty")


if __name__ == "__main__":
    unittest.main()
