"""E2E cases: each key result, run as the guide's Walkthrough runs it, at the guide's size.

The command runs in its own process as the colleague's terminal runs it, `print` with its
arguments, from the checked-out code by `python3 -m invoicer`, never an `invoicer` found on PATH,
so a copy installed on the machine changes no result; a stand-in `lp` on PATH takes the place of
the laptop's printing system."""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from decimal import Decimal

from tests import helpers


DECOY = """#!/bin/sh
echo "an installed invoicer ran in place of the checked-out code" >&2
exit 3
"""


def run_invoicer(args, folder):
    """Runs `python3 -m invoicer <args>` in folder on the checked-out code, by the Python that
    runs the tests, with folder first on PATH for its stand-in `lp`."""
    env = dict(
        os.environ,
        PATH=folder + os.pathsep + os.environ.get("PATH", ""),
        PYTHONPATH=helpers.ROOT,
    )
    return subprocess.run(
        [sys.executable, "-m", "invoicer"] + args,
        cwd=folder,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


class ColleaguePrintsTheGuidesInvoice(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        helpers.put_lp(self.folder)
        # An `invoicer` first on PATH that fails, so a case passes only on the checked-out code.
        decoy = os.path.join(self.folder, "invoicer")
        with open(decoy, "w", encoding="utf-8") as script:
            script.write(DECOY)
        os.chmod(decoy, 0o755)

    def test_nordwind_invoice_comes_out_of_the_printer_as_the_guide_shows(self):
        """Supports: KR1.1

        Given the guide's `nordwind-2026-11.ods`, saved as Calc saves it, and a default printer.
        When the colleague runs `invoicer print nordwind-2026-11.ods --rate 19`.
        Then the command says which invoice it printed for whom, exits 0, and the printer gets
        the guide's page, its lines, totals, and 19% tax right."""
        helpers.write_ods(os.path.join(self.folder, "nordwind-2026-11.ods"), helpers.nordwind_rows())

        done = run_invoicer(["print", "nordwind-2026-11.ods", "--rate", "19"], self.folder)

        self.assertEqual(
            done.stdout.strip(),
            "Printed invoice 2026-041 for Nordwind Handel GmbH on your default printer.",
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        record = helpers.lp_record(self.folder)
        self.assertIsNotNone(record, "the printer got nothing")
        self.assertEqual(record["text"], helpers.guide_page() + "\n")
        self.assertEqual(done.stderr, "")

    def test_wrong_cell_in_nordwind_sheet_is_named_and_nothing_is_printed(self):
        """Supports: KR1.1

        Given the guide's Nordwind sheet with the price of row 11 left empty.
        When the colleague runs `invoicer print nordwind-2026-11.ods --rate 19`.
        Then the command shows `row 11: the price is empty` and that nothing was printed, exits
        1, and the printer gets nothing."""
        lines = [list(line) for line in helpers.NORDWIND_LINES]
        lines[1][1] = None
        helpers.write_ods(
            os.path.join(self.folder, "nordwind-2026-11.ods"), helpers.nordwind_rows(lines=lines)
        )

        done = run_invoicer(["print", "nordwind-2026-11.ods", "--rate", "19"], self.folder)

        self.assertEqual(done.stderr, f"row 11: the price is empty\n{helpers.NOTHING_PRINTED}\n")
        self.assertEqual(done.stdout, "")
        self.assertEqual(done.returncode, 1)
        self.assertIsNone(helpers.lp_record(self.folder))

    def test_saved_sheet_becomes_a_printed_invoice_in_one_quick_command(self):
        """Supports: KR1.2

        Given the guide's Nordwind sheet, saved, which is where the colleague's timed task starts.
        When the colleague runs the Walkthrough's one command on it.
        Then the invoice reaches the printer within 5 seconds of the command starting, with no
        other step between the saved sheet and the printer."""
        helpers.write_ods(os.path.join(self.folder, "nordwind-2026-11.ods"), helpers.nordwind_rows())

        started = time.monotonic()
        done = run_invoicer(["print", "nordwind-2026-11.ods", "--rate", "19"], self.folder)
        took = time.monotonic() - started

        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIsNotNone(helpers.lp_record(self.folder), "the printer got nothing")
        self.assertLess(took, 5)

    def test_month_of_sixty_lines_prints_whole_past_one_page_and_quickly(self):
        """Supports: KR1.1, KR1.2

        Given Nordwind's sheet for the whole of November, as accounting sends a client each month:
        60 lines under its header, hours of bookkeeping, some of them 2.5, and receipts filed,
        saved as Calc saves it.
        When the colleague runs `invoicer print nordwind-2026-11.ods --rate 19`.
        Then within 5 seconds the command says it printed invoice 2026-041 for Nordwind, exits 0,
        and the printer gets one page text that runs past one printed sheet and holds every one
        of the 60 lines in the sheet's order, then the subtotal, the 19% tax, and the total
        right to the cent."""
        lines = helpers.month_lines()
        helpers.write_ods(
            os.path.join(self.folder, "nordwind-2026-11.ods"), helpers.nordwind_rows(lines=lines)
        )
        subtotal, tax, total = helpers.totals_of(lines)

        started = time.monotonic()
        done = run_invoicer(["print", "nordwind-2026-11.ods", "--rate", "19"], self.folder)
        took = time.monotonic() - started

        self.assertEqual(
            done.stdout.strip(),
            "Printed invoice 2026-041 for Nordwind Handel GmbH on your default printer.",
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        record = helpers.lp_record(self.folder)
        self.assertIsNotNone(record, "the printer got nothing")
        rows = record["text"].splitlines()
        self.assertGreater(len(rows), helpers.ROWS_ON_ONE_SHEET)
        billed = [row for row in rows if row.startswith(("Bookkeeping 11-", "Receipts filed 11-"))]
        self.assertEqual([row.split("  ")[0] for row in billed], [line[0] for line in lines])
        self.assertRegex(next(row for row in rows if row.startswith("Subtotal")), rf"\s{subtotal:.2f} EUR$")
        self.assertRegex(next(row for row in rows if row.startswith("Tax 19%")), rf"\s{tax:.2f} EUR$")
        self.assertRegex(next(row for row in rows if row.startswith("Total")), rf"\s{total:.2f} EUR$")
        self.assertLess(took, 5)


class DeveloperCallsTheLibraryAsBefore(unittest.TestCase):
    def test_existing_calls_give_the_invoice_text_they_gave_before(self):
        """Supports: KR2.1

        Given a developer's code that builds an invoice with the library's public names as
        invoicer 1.4.0 offered them.
        When it parses its lines, takes their totals and tax, and renders the invoice.
        Then each call gives what it gave in 1.4.0."""
        import invoicer

        lines = invoicer.parse_lines("A;10.00;2\nB;0.125;3\n")
        rate = Decimal("0.19")

        self.assertEqual(invoicer.subtotal(lines), Decimal("20.375"))
        self.assertEqual(invoicer.tax_of(invoicer.subtotal(lines), rate), Decimal("3.87"))
        self.assertEqual(invoicer.total(lines, rate), Decimal("24.245"))
        self.assertEqual(
            invoicer.render(lines, rate),
            "A                                    20.00 EUR\n"
            "B                                    0.375 EUR\n"
            "Subtotal                            20.375 EUR\n"
            "Tax                                   3.87 EUR\n"
            "Total                               24.245 EUR",
        )


if __name__ == "__main__":
    unittest.main()
