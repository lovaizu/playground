"""Unit cases of printer.print_page: `lp` taking the page, `lp` refusing it, and `lp` missing, each
with a stand-in `lp` on PATH or none."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from invoicer import printer
from tests import helpers

PAGE = "Lindqvist Buchhaltung GmbH\nHauptstraße 5, 10115 Berlin\n\nTotal  1429.19 EUR\n"


class PrinterCase(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)

    def on_path(self, folder):
        path = mock.patch.dict(os.environ, {"PATH": folder + os.pathsep + os.environ.get("PATH", "")})
        path.start()
        self.addCleanup(path.stop)


class HandsThePageToLp(PrinterCase):
    def test_lp_gets_the_page_for_the_default_printer(self):
        """Supports: PrintsTheInvoice.test_page_goes_to_the_default_printer

        Given an `lp` on PATH that takes the page.
        When print_page gets a page.
        Then `lp` gets the page's text on its standard input and no argument at all, so no
        printer or option is named, and print_page refuses nothing."""
        helpers.put_lp(self.folder)
        self.on_path(self.folder)

        self.assertIsNone(printer.print_page(PAGE))

        record = helpers.lp_record(self.folder)
        self.assertIsNotNone(record, "lp never ran")
        self.assertEqual(record, {"args": [], "text": PAGE})

    def test_page_longer_than_one_sheet_goes_to_lp_whole(self):
        """Supports: PrintsTheInvoice.test_month_of_lines_reaches_the_printer_whole

        Given an `lp` on PATH that takes the page, and a page of more rows than one printed
        sheet holds, as a month's invoice runs.
        When print_page gets it.
        Then `lp` gets the whole page, every row in order, to break across sheets itself."""
        helpers.put_lp(self.folder)
        self.on_path(self.folder)
        long_page = "".join(f"Bookkeeping 11-{row:02}  80.00 EUR\n" for row in range(1, 100))

        self.assertIsNone(printer.print_page(long_page))

        record = helpers.lp_record(self.folder)
        self.assertIsNotNone(record, "lp never ran")
        self.assertGreater(len(record["text"].splitlines()), helpers.ROWS_ON_ONE_SHEET)
        self.assertEqual(record["text"], long_page)

    def test_lp_refusing_for_want_of_a_default_printer(self):
        """Supports: NoPrinterTakesThePage.test_printer_refusing_is_told_with_nothing_printed

        Given an `lp` on PATH that says `lp: Error - no default destination available.` and exits
        1, as it does with no default printer.
        When print_page gets a page.
        Then it refuses with PrintError, giving `lp`'s reason and then to set a default printer."""
        helpers.put_lp(self.folder, status=1, says="lp: Error - no default destination available.\n")
        self.on_path(self.folder)

        with self.assertRaises(printer.PrintError) as refused:
            printer.print_page(PAGE)

        self.assertEqual(
            str(refused.exception),
            "lp: Error - no default destination available: set a default printer in Settings, "
            "then Printers, and check that `lpstat -d` shows it",
        )
        self.assertIsNotNone(helpers.lp_record(self.folder), "lp never ran")

    def test_lp_refusing_with_its_own_reason(self):
        """Supports: PrinterGivesItsOwnReason.test_printers_own_reason_is_told

        Given an `lp` on PATH that says `lp: The printer or class does not exist.` and exits 1, as
        it does where the default printer was removed.
        When print_page gets a page.
        Then it refuses with PrintError whose message is that reason alone."""
        helpers.put_lp(self.folder, status=1, says="lp: The printer or class does not exist.\n")
        self.on_path(self.folder)

        with self.assertRaises(printer.PrintError) as refused:
            printer.print_page(PAGE)

        self.assertEqual(str(refused.exception), "lp: The printer or class does not exist.")

    def test_lp_refusing_with_no_reason(self):
        """Supports: NoPrinterTakesThePage.test_printer_refusing_is_told_with_nothing_printed

        Given an `lp` on PATH that exits 1 and says nothing.
        When print_page gets a page.
        Then it refuses with PrintError, saying no printer took the invoice and to set a default
        printer."""
        helpers.put_lp(self.folder, status=1)
        self.on_path(self.folder)

        with self.assertRaises(printer.PrintError) as refused:
            printer.print_page(PAGE)

        self.assertEqual(
            str(refused.exception),
            "no printer took the invoice: set a default printer in Settings, then Printers, and "
            "check that `lpstat -d` shows it",
        )

    def test_lp_missing(self):
        """Supports: NoPrinterTakesThePage.test_missing_printing_command_is_told_with_nothing_printed

        Given a PATH that holds no `lp`.
        When print_page gets a page.
        Then it refuses with PrintError, saying `lp` isn't on this laptop and to set a default
        printer."""
        with mock.patch.dict(os.environ, {"PATH": self.folder}):
            with self.assertRaises(printer.PrintError) as refused:
                printer.print_page(PAGE)

        self.assertEqual(
            str(refused.exception),
            "the printing command `lp` isn't on this laptop: set a default printer in Settings, "
            "then Printers, and check that `lpstat -d` shows it",
        )


if __name__ == "__main__":
    unittest.main()
