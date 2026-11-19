"""Integration cases: the Command joined with the Rate reader, the Sheet reader, the Invoice page,
and the Printer, run on .ods sheets the tests build, with a stand-in `lp` on PATH that records what
it got. Each case names the stories, branches, principle items, components, and data it supports,
as tests/trace.py reads them."""

import ast
import contextlib
import importlib.util
import io
import os
import shutil
import sys
import sysconfig
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

from invoicer import cli, page, rate, sheet
from tests import helpers

PRINTED = "Printed invoice 2026-041 for Nordwind Handel GmbH on your default printer."


class CommandCase(unittest.TestCase):
    """A folder with a stand-in `lp` first on PATH, and the command run in it."""

    lp_status = 0
    lp_says = ""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        helpers.put_lp(self.folder, status=self.lp_status, says=self.lp_says)
        path = mock.patch.dict(
            os.environ, {"PATH": self.folder + os.pathsep + os.environ.get("PATH", "")}
        )
        path.start()
        self.addCleanup(path.stop)

    def sheet(self, rows=None, name="nordwind-2026-11.ods", more_sheets=()):
        path = os.path.join(self.folder, name)
        return helpers.write_ods(path, helpers.nordwind_rows() if rows is None else rows, more_sheets)

    def run_command(self, *argv):
        """Runs cli.main(argv), and gives its status, standard output, and standard error, an exit
        through SystemExit counting as its status."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                status = cli.main(list(argv))
            except SystemExit as stop:
                status = stop.code
        return status, out.getvalue(), err.getvalue()

    def printed(self):
        return helpers.lp_record(self.folder)

    def assertRefused(self, done, said):
        """The command exited 1, said on standard error the rows of said and nothing else, said
        nothing on standard output, and the printer got nothing."""
        status, out, err = done
        self.assertEqual(err.splitlines(), said)
        self.assertEqual(status, 1)
        self.assertEqual(out, "")
        self.assertIsNone(self.printed(), "the printer got a page")


def nordwind_with(row, column, value):
    """The Nordwind rows with the cell at the 1-based row and the 0-based column set to value."""
    rows = helpers.nordwind_rows()
    rows[row - 1][column] = value
    return rows


class PrintsTheInvoice(CommandCase):
    def test_prints_the_sheets_invoice_at_the_typed_rate(self):
        """Supports: S1, Command, Rate reader, Sheet reader, Invoice page, Printer, Sheet file

        Given the Nordwind sheet saved as Calc saves it, and a default printer.
        When the command runs `print nordwind-2026-11.ods --rate 19`.
        Then it says which invoice it printed for whom, exits 0, and the printer gets the guide's
        page."""
        path = self.sheet()

        status, out, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(out.strip(), PRINTED)
        self.assertEqual(status, 0, err)
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        self.assertEqual(self.printed()["text"].rstrip("\n"), helpers.guide_page())

    def test_page_the_printer_gets_is_made_from_the_sheets_details_lines_and_rate(self):
        """Supports: S1, Invoice details, Lines, Rate, Invoice page

        Given the Nordwind sheet, and the details and lines the Sheet reader reads from it, and
        the rate the Rate reader reads from `19%`.
        When the command runs `print <sheet> --rate 19%`.
        Then the printer gets the very page the Invoice page makes of those details, lines, and
        rate."""
        path = self.sheet()
        read = sheet.read_sheet(path)
        self.assertIsInstance(read, tuple)
        details, lines = read
        expected = page.render_page(details, lines, rate.parse_rate("19%"))
        self.assertIsInstance(expected, str)

        status, _, err = self.run_command("print", path, "--rate", "19%")

        self.assertEqual(status, 0, err)
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        self.assertEqual(self.printed()["text"].rstrip("\n"), expected.rstrip("\n"))

    def test_message_names_the_sheets_invoice_number_and_client(self):
        """Supports: S1, Command, Invoice details

        Given a sheet for another client, invoice 2026-042 for Ostsee Logistik AG.
        When the command prints it at 7%.
        Then the command says `Printed invoice 2026-042 for Ostsee Logistik AG on your default
        printer.`, and the page bills Ostsee Logistik AG under 2026-042 at `Tax 7%`."""
        details = [list(row) for row in helpers.NORDWIND_DETAILS]
        details[0][1] = "2026-042"
        details[2][1] = "Ostsee Logistik AG"
        path = self.sheet(helpers.nordwind_rows(details=details))

        status, out, err = self.run_command("print", path, "--rate", "7")

        self.assertEqual(
            out.strip(), "Printed invoice 2026-042 for Ostsee Logistik AG on your default printer."
        )
        self.assertEqual(status, 0, err)
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        text = self.printed()["text"]
        for each in ("Ostsee Logistik AG", "Invoice 2026-042", "Tax 7%"):
            self.assertIn(each, text)

    def test_lines_as_accounting_keeps_them_bill_right(self):
        """Supports: S1, Sheet reader, Invoice details, Lines, Invoice page

        Given the Nordwind sheet as German accounting types it: the date typed as text, day
        first with points between, 2.5 bookkeeping hours at a price pasted as the text `80,00`,
        a description longer than the page's column, a discount line of -50.00, and a free first
        consultation at 0.
        When the command prints it at 19%.
        Then the printer gets a page with the date as typed, 2.5 hours for 200.00 EUR, the long
        description wrapped whole in its column, the discount and the free line, and a subtotal
        of 500.00 EUR, a tax of 95.00 EUR, and a total of 595.00 EUR."""
        details = [list(row) for row in helpers.NORDWIND_DETAILS]
        details[1][1] = "19.11.2026"
        long = "Annual accounts and the tax return for the year 2025"
        lines = [
            ["Bookkeeping hours", "80,00", Decimal("2.5")],
            [long, Decimal("350.00"), 1],
            ["Early payment", Decimal("-50.00"), 1],
            ["First consultation", Decimal("0"), 1],
        ]
        path = self.sheet(helpers.nordwind_rows(lines=lines, details=details))

        status, _, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(status, 0, err)
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        self.assertEqual(
            self.printed()["text"],
            "Lindqvist Buchhaltung GmbH\n"
            "Hauptstraße 5, 10115 Berlin\n"
            "VAT ID DE123456789\n"
            "\n"
            "Nordwind Handel GmbH\n"
            "Hafenweg 12, 20457 Hamburg\n"
            "\n"
            "Invoice 2026-041\n"
            "Date 19.11.2026\n"
            "\n"
            + "Description           Quantity    Unit price        Amount\n"
            + "Bookkeeping hours          2.5     80.00 EUR    200.00 EUR\n"
            + "Annual accounts and          1    350.00 EUR    350.00 EUR\n"
            + "the tax return for\n"
            + "the year 2025\n"
            + "Early payment                1    -50.00 EUR    -50.00 EUR\n"
            + "First consultation           1      0.00 EUR      0.00 EUR\n"
            + "\n"
            + "Subtotal                                        500.00 EUR\n"
            + "Tax 19%                                          95.00 EUR\n"
            + "Total                                           595.00 EUR\n"
        )

    def test_price_in_a_currency_cell_bills_its_value(self):
        """Supports: S1, Sheet reader, Lines, Invoice page

        Given the Nordwind sheet whose price in row 10 accounting formatted as Currency, which
        Calc shows as `80,00 €` and stores as 80.
        When the command prints it at 19%.
        Then it exits 0 and the printer gets the guide's page, the hours at 80.00 EUR."""
        path = self.sheet(nordwind_with(10, 1, ("currency", "80", "80,00 €")))

        status, out, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual((status, out.strip(), err), (0, PRINTED, ""))
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        self.assertEqual(self.printed()["text"], helpers.guide_page() + "\n")

    def test_rate_typed_with_a_comma_a_point_or_a_sign_prints_at_that_rate(self):
        """Supports: S1, Rate reader, Rate, Invoice page

        Given the Nordwind sheet, whose subtotal is 1201.00 EUR.
        When the command prints it with `--rate 19,5`, `--rate 19.5`, and `--rate "19 %"`.
        Then the printer gets `Tax 19.5%` of 234.20 EUR for each of the first two, and `Tax 19%`
        of 228.19 EUR for the third."""
        path = self.sheet()
        record = os.path.join(self.folder, "lp-record.json")
        for typed, tax_row in (
            ("19,5", r"^Tax 19\.5%\s+234\.20 EUR$"),
            ("19.5", r"^Tax 19\.5%\s+234\.20 EUR$"),
            ("19 %", r"^Tax 19%\s+228\.19 EUR$"),
        ):
            with self.subTest(rate=typed):
                if os.path.exists(record):
                    os.remove(record)

                status, _, err = self.run_command("print", path, "--rate", typed)

                self.assertEqual(status, 0, err)
                self.assertIsNotNone(self.printed(), "the printer got nothing")
                rows = self.printed()["text"].splitlines()
                self.assertRegex(next((row for row in rows if row.startswith("Tax ")), ""), tax_row)

    def test_month_of_lines_reaches_the_printer_whole(self):
        """Supports: S1, Invoice page, Printer, Lines

        Given the Nordwind sheet for all of November, 60 lines.
        When the command prints it at 19%.
        Then `lp` gets the whole page, more rows than one printed sheet holds, for it
        to break across sheets: every one of the 60 lines, and the total right to the cent."""
        lines = helpers.month_lines()
        path = self.sheet(helpers.nordwind_rows(lines=lines))
        _, _, total = helpers.totals_of(lines)

        status, _, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(status, 0, err)
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        rows = self.printed()["text"].splitlines()
        self.assertGreater(len(rows), helpers.ROWS_ON_ONE_SHEET)
        for description, _, _ in lines:
            self.assertTrue(any(row.startswith(description + " ") for row in rows), description)
        self.assertRegex(next(row for row in rows if row.startswith("Total")), rf"\s{total:.2f} EUR$")

    def test_page_goes_to_the_default_printer(self):
        """Supports: S1, P3, Printer

        Given the Nordwind sheet and a default printer.
        When the command prints it.
        Then it hands the page to `lp` with no argument, naming no printer or option, so the
        default printer takes it."""
        path = self.sheet()

        status, _, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(status, 0, err)
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        self.assertEqual(self.printed()["args"], [], "lp is called with no argument")

    def test_header_in_any_column_order_bills_the_same_lines(self):
        """Supports: S1, Sheet reader, Lines

        Given the Nordwind sheet with its header row as `Quantity`, `Description`, `Price`, and
        each line's cells in that order.
        When the command prints it at 19%.
        Then the printer gets the guide's page."""
        lines = [[quantity, description, price] for description, price, quantity in helpers.NORDWIND_LINES]
        path = self.sheet(helpers.nordwind_rows(lines=lines, header=["Quantity", "Description", "Price"]))

        status, _, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(status, 0, err)
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        self.assertEqual(self.printed()["text"].rstrip("\n"), helpers.guide_page())

    def test_only_the_first_sheet_is_read(self):
        """Supports: S1, Sheet reader, Sheet file

        Given the Nordwind file whose second sheet holds other notes.
        When the command prints it at 19%.
        Then the printer gets the guide's page, made from the first sheet alone."""
        path = self.sheet(more_sheets=[[["Description", "Price", "Quantity"], ["Other", 1, 1]]])

        status, _, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(status, 0, err)
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        self.assertEqual(self.printed()["text"].rstrip("\n"), helpers.guide_page())


class MoneyToTheCent(CommandCase):
    def test_amounts_are_rounded_to_the_cent_and_the_page_adds_up(self):
        """Supports: P2, Invoice page, Lines, Rate

        Given a sheet whose first line's price a formula gave as 400.333333333333, shown by Calc
        as 400.33, and whose second line is 3 stamps at 0.125, at 19%.
        When the command prints it.
        Then the page shows 400.33 EUR, 3 at 0.13 EUR for 0.39 EUR, the subtotal 400.72 EUR as
        the sum of the shown amounts, the tax 76.14 EUR rounded half up, and the total
        476.86 EUR, so every figure on it adds up."""
        lines = [["Annual accounts", Decimal("400.333333333333"), 1], ["Stamp", Decimal("0.125"), 3]]
        path = self.sheet(helpers.nordwind_rows(lines=lines))

        status, _, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(status, 0, err)
        self.assertIsNotNone(self.printed(), "the printer got nothing")
        self.assertEqual(
            self.printed()["text"],
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
            + "Description           Quantity    Unit price        Amount\n"
            + "Annual accounts              1    400.33 EUR    400.33 EUR\n"
            + "Stamp                        3      0.13 EUR      0.39 EUR\n"
            + "\n"
            + "Subtotal                                        400.72 EUR\n"
            + "Tax 19%                                          76.14 EUR\n"
            + "Total                                           476.86 EUR\n"
        )


class RefusesWhatIsWrong(CommandCase):
    def test_wrong_rate_is_refused_before_anything_is_printed(self):
        """Supports: S2, S2: rate wrong, P4, Rate reader, Refusal

        Given the Nordwind sheet.
        When the command runs with `--rate nineteen`.
        Then it says the rate isn't a number and to fix the rate, not the sheet, exits 1, and the
        printer gets nothing."""
        path = self.sheet()

        done = self.run_command("print", path, "--rate", "nineteen")

        self.assertRefused(
            done,
            [
                "the rate `nineteen` isn't a number: type the client's tax rate as a percent from "
                "0 to 100, such as --rate 19",
                helpers.FIX_THE_RATE,
            ],
        )

    def test_rate_typed_as_a_fraction_is_refused(self):
        """Supports: S2, S2: rate wrong, P4, Rate reader, Refusal

        Given the Nordwind sheet.
        When the command runs with `--rate 0.19`, the fraction typed for 19%.
        Then it says to type the rate as a percent, such as 19 for 19%, and to fix the rate,
        exits 1, and the printer gets nothing, so no invoice goes out at 0.19%."""
        path = self.sheet()

        done = self.run_command("print", path, "--rate", "0.19")

        self.assertRefused(
            done,
            [
                "the rate `0.19` is below 1%: type the rate as a percent, such as 19 for 19%",
                helpers.FIX_THE_RATE,
            ],
        )

    def test_rate_is_read_before_the_sheet(self):
        """Supports: S2, S2: rate wrong, Command, Rate reader

        Given no sheet at the path given, and a rate of more than 100.
        When the command runs `print missing.ods --rate 190`.
        Then the refusal it shows is the rate's alone, as the Rate reader runs first."""
        done = self.run_command("print", os.path.join(self.folder, "missing.ods"), "--rate", "190")

        self.assertRefused(
            done,
            [
                "the rate `190` is outside 0 to 100: type the client's tax rate as a percent from 0 "
                "to 100, such as --rate 19",
                helpers.FIX_THE_RATE,
            ],
        )

    def test_missing_file_is_refused(self):
        """Supports: S2, S2: file missing, P4, Sheet reader, Refusal

        Given no file at `missing.ods`.
        When the command runs `print missing.ods --rate 19`.
        Then it names the file it couldn't find and that nothing was printed, exits 1, and the
        printer gets nothing."""
        path = os.path.join(self.folder, "missing.ods")

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            [f"{path}: there's no such file: check the sheet's name and folder", helpers.NOTHING_PRINTED],
        )

    def test_folder_is_refused(self):
        """Supports: S2, S2: file missing, P4, Sheet reader, Refusal

        Given the folder that holds the sheet, given in place of the sheet.
        When the command runs `print <folder> --rate 19`.
        Then it says the path is a folder and to give the .ods file inside it, with no
        traceback, exits 1, and the printer gets nothing."""
        done = self.run_command("print", self.folder, "--rate", "19")

        self.assertRefused(
            done, [f"{self.folder} is a folder; give the .ods file inside it", helpers.NOTHING_PRINTED]
        )

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root may read any file")
    def test_sheet_it_may_not_read_is_refused(self):
        """Supports: S2, S2: file missing, P4, Sheet reader, Refusal

        Given the Nordwind sheet shared with no permission for the colleague to read it.
        When the command runs `print nordwind-2026-11.ods --rate 19`.
        Then it names the file, says it may not read it and to ask whoever shared it for access,
        with no traceback, and that nothing was printed, exits 1, and the printer gets nothing."""
        path = self.sheet()
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            [
                f"{path} can't be opened: you may not read it. Ask whoever shared it to give you "
                "access.",
                helpers.NOTHING_PRINTED,
            ],
        )

    def test_file_that_isnt_an_ods_is_refused(self):
        """Supports: S2, S2: not an .ods, P3, P4, Sheet reader, Refusal

        Given the Nordwind lines exported as a .csv file in place of the .ods Calc saves.
        When the command runs `print nordwind-2026-11.csv --rate 19`.
        Then it names the file, says it isn't an .ods, and that nothing was printed, exits 1, and
        the printer gets nothing."""
        path = os.path.join(self.folder, "nordwind-2026-11.csv")
        with open(path, "w", encoding="utf-8") as csv:
            csv.write("Description,Price,Quantity\nBookkeeping hours,80.00,10\n")

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            [
                f"{path} isn't an .ods spreadsheet: save the sheet in Calc as ODF Spreadsheet (.ods)",
                helpers.NOTHING_PRINTED,
            ],
        )

    def test_missing_label_is_refused(self):
        """Supports: S2, S2: label missing, P4, Sheet reader, Invoice details, Refusal

        Given the Nordwind sheet without the row of the seller's VAT ID.
        When the command prints it at 19%.
        Then it names the missing label and where it goes, and that nothing was printed, exits
        1, and the printer gets nothing."""
        path = self.sheet(helpers.nordwind_rows(details=helpers.NORDWIND_DETAILS[:-1]))

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            [
                "the `Our VAT ID` row is missing: put `Our VAT ID` in column A of a row above the "
                "header and its value in column B",
                helpers.NOTHING_PRINTED,
            ],
        )

    def test_label_given_twice_is_refused_naming_both_rows(self):
        """Supports: S2, S2: label missing, P4, Sheet reader, Invoice details, Refusal

        Given the Nordwind sheet with a second `Invoice number` row, 2026-040, left from the
        last invoice under the first.
        When the command prints it at 19%.
        Then it names rows 1 and 2 and says to keep one, exits 1, and the printer gets nothing,
        so no invoice goes out under the wrong number."""
        details = [list(row) for row in helpers.NORDWIND_DETAILS]
        details.insert(1, ["Invoice number", "2026-040"])
        path = self.sheet(helpers.nordwind_rows(details=details))

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            [
                "rows 1 and 2 both hold the label `Invoice number`: keep the row with this "
                "invoice's value and delete the other",
                helpers.NOTHING_PRINTED,
            ],
        )

    def test_label_with_an_empty_value_is_refused_naming_its_row(self):
        """Supports: S2, S2: cell wrong, P4, Sheet reader, Invoice details, Refusal

        Given the Nordwind sheet whose `Client name` label stands in row 3 with nothing beside it.
        When the command prints it at 19%.
        Then it says `row 3: the Client name is empty` and that nothing was printed, exits 1, and
        the printer gets nothing, so no invoice goes out without the client it bills."""
        path = self.sheet(nordwind_with(3, 1, None))

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(done, ["row 3: the Client name is empty", helpers.NOTHING_PRINTED])

    def test_missing_header_is_refused(self):
        """Supports: S2, S2: header missing, P4, Sheet reader, Refusal

        Given the Nordwind sheet whose header row 9 names `Item` in place of `Description`.
        When the command prints it at 19%.
        Then it names row 9 and the missing Description column, and that nothing was printed,
        exits 1, and the printer gets nothing."""
        path = self.sheet(helpers.nordwind_rows(header=["Item", "Price", "Quantity"]))

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            [
                "row 9: the header has no Description column: name its column Description, as "
                "Description, Price, and Quantity",
                helpers.NOTHING_PRINTED,
            ],
        )

    def test_wrong_cell_is_refused_naming_its_row(self):
        """Supports: S2, S2: cell wrong, P4, Sheet reader, Refusal

        Given the Nordwind sheet with the price of row 11 empty.
        When the command prints it at 19%.
        Then it says `row 11: the price is empty` and that nothing was printed, exits 1, and the
        printer gets nothing."""
        path = self.sheet(nordwind_with(11, 1, None))

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(done, ["row 11: the price is empty", helpers.NOTHING_PRINTED])

    def test_price_that_reads_two_ways_is_refused(self):
        """Supports: S2, S2: cell wrong, P4, Sheet reader, Refusal

        Given the Nordwind sheet whose price in row 11 is typed as the text `1.200`, twelve
        hundred as German accounting writes it, which would otherwise bill 1.20.
        When the command prints it at 19%.
        Then it says `row 11: write the price as a plain number, such as 1200.00`, exits 1, and
        the printer gets nothing."""
        path = self.sheet(nordwind_with(11, 1, "1.200"))

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            ["row 11: write the price as a plain number, such as 1200.00", helpers.NOTHING_PRINTED],
        )

    def test_quantity_that_reads_two_ways_is_refused(self):
        """Supports: S2, S2: cell wrong, P4, Sheet reader, Refusal

        Given the Nordwind sheet whose quantity in row 10 is typed as the text `1.000`, a
        thousand as German accounting writes it, which would otherwise bill 1.
        When the command prints it at 19%.
        Then it says `row 10: write the quantity as a plain number, such as 1000` and that
        nothing was printed, exits 1, and the printer gets nothing."""
        path = self.sheet(nordwind_with(10, 2, "1.000"))

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            ["row 10: write the quantity as a plain number, such as 1000", helpers.NOTHING_PRINTED],
        )

    def test_line_below_an_empty_row_is_refused_naming_both_rows(self):
        """Supports: S2, S2: cell wrong, P1, P4, Sheet reader, Lines, Refusal

        Given the Nordwind sheet with row 13 empty and a postage line added in row 14 under it.
        When the command prints it at 19%.
        Then it names row 14 and the empty row 13, exits 1, and the printer gets nothing, as an
        invoice without the postage would bill too little."""
        rows = helpers.nordwind_rows() + [[], ["Postage", Decimal("4.50"), 1]]
        path = self.sheet(rows)

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            [
                "row 14 holds text below the empty row 13, where the lines end: delete the empty "
                "row 13 to bill row 14, or clear row 14",
                helpers.NOTHING_PRINTED,
            ],
        )

    def test_wrong_last_line_stops_the_whole_invoice(self):
        """Supports: P1, S2: cell wrong, Command, Sheet reader, Printer

        Given the Nordwind sheet whose first two lines are right and whose last line, row 12, has
        the quantity `two`.
        When the command prints it at 19%.
        Then it names row 12 and the quantity, and the printer gets nothing, not even the first
        two lines, since nothing reaches the printer until the whole sheet is checked."""
        path = self.sheet(nordwind_with(12, 2, "two"))

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            [
                "row 12: the quantity `two` isn't a number: type how many as a number, such as 10",
                helpers.NOTHING_PRINTED,
            ],
        )

    def test_sheet_with_no_lines_is_refused(self):
        """Supports: S2, S2: no lines, P4, Sheet reader, Refusal

        Given the Nordwind sheet with its header row 9 and no line under it.
        When the command prints it at 19%.
        Then it says the sheet has no lines and where they go, and that nothing was printed,
        exits 1, and the printer gets nothing."""
        path = self.sheet(helpers.nordwind_rows(lines=[]))

        done = self.run_command("print", path, "--rate", "19")

        self.assertRefused(
            done,
            [
                "the sheet has no lines: put each line in the rows right under the header in row 9",
                helpers.NOTHING_PRINTED,
            ],
        )


class NoPrinterTakesThePage(CommandCase):
    lp_status = 1
    lp_says = "lp: Error - no default destination available.\n"

    def test_printer_refusing_is_told_with_nothing_printed(self):
        """Supports: S2, S2: no printer, P4, Printer, Refusal

        Given the Nordwind sheet, and a printing system whose `lp` says `lp: Error - no default
        destination available.` and exits 1, as it does with no default printer.
        When the command prints the sheet at 19%.
        Then it gives `lp`'s reason, says to set a default printer and that nothing was printed,
        not to fix the sheet, and exits 1."""
        path = self.sheet()

        status, out, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(
            err.splitlines(),
            [
                f"lp: Error - no default destination available: {helpers.SET_A_PRINTER}",
                helpers.FIX_THE_PRINTER,
            ],
        )
        self.assertEqual((status, out), (1, ""))

    def test_missing_printing_command_is_told_with_nothing_printed(self):
        """Supports: S2, S2: no printer, P3, Printer, Refusal

        Given the Nordwind sheet, and a laptop whose PATH holds no `lp`.
        When the command prints the sheet at 19%.
        Then it says `lp` isn't on this laptop, to set a default printer, and that nothing was
        printed, and exits 1."""
        path = self.sheet()
        empty = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty)

        with mock.patch.dict(os.environ, {"PATH": empty}):
            status, out, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(
            err.splitlines(),
            [
                f"the printing command `lp` isn't on this laptop: {helpers.SET_A_PRINTER}",
                helpers.FIX_THE_PRINTER,
            ],
        )
        self.assertEqual((status, out), (1, ""))


class PrinterGivesItsOwnReason(CommandCase):
    lp_status = 1
    lp_says = "lp: The printer or class does not exist.\n"

    def test_printers_own_reason_is_told(self):
        """Supports: S2, S2: no printer, P4, Printer, Refusal

        Given the Nordwind sheet, and an `lp` that says `lp: The printer or class does not
        exist.` and exits 1, as it does where the default printer was removed.
        When the command prints the sheet at 19%.
        Then it shows that reason and that nothing was printed, and exits 1."""
        path = self.sheet()

        status, out, err = self.run_command("print", path, "--rate", "19")

        self.assertEqual(
            err.splitlines(), ["lp: The printer or class does not exist.", helpers.FIX_THE_PRINTER]
        )
        self.assertEqual((status, out), (1, ""))


class AnswersAfterInstalling(CommandCase):
    def test_help_shows_the_usage_line(self):
        """Supports: S3, Command

        Given invoicer installed by the guide.
        When the colleague runs `invoicer --help`.
        Then it shows `usage: invoicer print SHEET --rate PERCENT`, exits 0, and prints nothing."""
        status, out, _ = self.run_command("--help")

        self.assertIn("usage: invoicer print SHEET --rate PERCENT", out)
        self.assertEqual(status, 0)
        self.assertIsNone(self.printed())

    def test_package_installs_the_invoicer_command(self):
        """Supports: S3, Command

        Given invoicer's pyproject.toml, which pipx installs from.
        When pipx reads its scripts.
        Then `invoicer` starts invoicer.cli:main, under version 1.5.0."""
        with open(os.path.join(helpers.ROOT, "pyproject.toml"), encoding="utf-8") as project:
            text = project.read()

        self.assertRegex(text, r'(?m)^\[project\.scripts\]\s*\ninvoicer = "invoicer\.cli:main"')
        self.assertRegex(text, r'(?m)^version = "1\.5\.0"$')

    def test_missing_rate_is_usage_and_prints_nothing(self):
        """Supports: S3, Command

        Given the Nordwind sheet.
        When the command runs `print <sheet>` with no `--rate`.
        Then it shows the usage line on standard error, exits 2, and the printer gets nothing."""
        path = self.sheet()

        status, _, err = self.run_command("print", path)

        self.assertIn("usage: invoicer print SHEET --rate PERCENT", err)
        self.assertEqual(status, 2)
        self.assertIsNone(self.printed())

    def test_word_other_than_print_is_usage_and_prints_nothing(self):
        """Supports: S3, Command

        Given the Nordwind sheet.
        When the command runs `prnt <sheet> --rate 19`, print mistyped.
        Then it shows the usage line on standard error, says nothing on standard output, exits 2,
        and the printer gets nothing."""
        path = self.sheet()

        status, out, err = self.run_command("prnt", path, "--rate", "19")

        self.assertEqual(err.splitlines()[0], "usage: invoicer print SHEET --rate PERCENT")
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        self.assertIsNone(self.printed(), "the printer got a page")

    def test_rate_given_twice_is_usage_and_prints_nothing(self):
        """Supports: S3, Command

        Given the Nordwind sheet.
        When the command runs `print <sheet> --rate 19 --rate 7`, two rates for one invoice.
        Then it shows the usage line and `invoicer: error: give the rate once, such as --rate 19`
        on standard error, says nothing on standard output, exits 2, and the printer gets
        nothing."""
        path = self.sheet()

        status, out, err = self.run_command("print", path, "--rate", "19", "--rate", "7")

        self.assertEqual(
            err,
            "usage: invoicer print SHEET --rate PERCENT\n"
            "invoicer: error: give the rate once, such as --rate 19\n",
        )
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        self.assertIsNone(self.printed(), "the printer got a page")

    def test_no_command_is_usage(self):
        """Supports: S3, Command

        Given invoicer installed.
        When the colleague runs `invoicer` with nothing after it.
        Then it shows the usage line on standard error and exits 2."""
        status, _, err = self.run_command()

        self.assertIn("usage: invoicer print SHEET --rate PERCENT", err)
        self.assertEqual(status, 2)


def in_standard_library(name, names=getattr(sys, "stdlib_module_names", None)):
    """Whether the top-level module name is of Python's standard library: by names where Python
    gives them, from 3.10 on, and on 3.9, which doesn't, by where the module lies, built in or
    under the standard library's folder and outside any folder of added packages."""
    if names is not None:
        return name in names
    if name in sys.builtin_module_names:
        return True
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin in (None, "namespace"):
        return False
    if spec.origin in ("built-in", "frozen"):
        return True
    origin = os.path.realpath(spec.origin)
    paths = sysconfig.get_paths()
    stdlib = {os.path.realpath(paths[key]) for key in ("stdlib", "platstdlib")}
    added = {os.path.realpath(paths[key]) for key in ("purelib", "platlib")}
    return (
        any(origin.startswith(folder + os.sep) for folder in stdlib)
        and not any(origin.startswith(folder + os.sep) for folder in added)
        and not {"site-packages", "dist-packages"} & set(origin.split(os.sep))
    )


class NothingIsAdded(unittest.TestCase):
    def test_invoicer_needs_only_pythons_standard_library(self):
        """Supports: P3, Sheet reader, Printer

        Given invoicer's modules and pyproject.toml, on any Python from 3.9 on, the lowest the
        deployment allows, which has no sys.stdlib_module_names.
        When their imports and dependencies are read.
        Then each import is of Python's standard library or of invoicer, and no dependency is
        declared, so the laptop needs nothing beyond Python. This case is a guard: it passes
        before the build, as nothing is added yet, and fails once a module imports a package,
        such as odfpy's `odf`, or pyproject.toml declares one."""
        for name, expected in (
            ("zipfile", True),
            ("decimal", True),
            ("xml", True),
            ("odf", False),
            ("openpyxl", False),
        ):
            with self.subTest(module=name):
                self.assertIs(in_standard_library(name), expected)
                self.assertIs(in_standard_library(name, names=None), expected)
        package = os.path.join(helpers.ROOT, "invoicer")
        found = set()
        for name in sorted(os.listdir(package)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(package, name), encoding="utf-8") as module:
                tree = ast.parse(module.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    found.add(node.module.split(".")[0])
        with open(os.path.join(helpers.ROOT, "pyproject.toml"), encoding="utf-8") as project:
            text = project.read()

        self.assertEqual({name for name in found - {"invoicer"} if not in_standard_library(name)}, set())
        self.assertNotRegex(text, r"(?m)^dependencies\s*=\s*\[\s*\S")
        self.assertIn("cli.py", os.listdir(package))
        self.assertIn("sheet.py", os.listdir(package))
        self.assertIn("printer.py", os.listdir(package))


class LibraryKeepsItsNames(unittest.TestCase):
    def test_public_names_stay_and_give_what_they_gave(self):
        """Supports: S4, P5, Library

        Given a developer's code that calls the names invoicer 1.4.0 made public.
        When it imports them and calls each with the arguments it used before.
        Then each name is still public and gives what it gave in 1.4.0."""
        import invoicer

        self.assertTrue(
            {"Line", "parse_lines", "render", "subtotal", "tax_of", "total"} <= set(invoicer.__all__)
        )
        lines = invoicer.parse_lines("Kaffee;2.50;4")
        self.assertEqual(
            invoicer.render(lines, Decimal("0.07"), "USD"),
            "Kaffee                               10.00 USD\n"
            "Subtotal                             10.00 USD\n"
            "Tax                                   0.70 USD\n"
            "Total                                10.70 USD",
        )
        self.assertEqual(invoicer.total(invoicer.parse_lines("x;1.10;3"), Decimal("0.19")), Decimal("3.93"))
        self.assertEqual(invoicer.Line("x", Decimal("2.50"), 4).amount(), Decimal("10.00"))


if __name__ == "__main__":
    unittest.main()
