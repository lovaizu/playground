"""The integration cases: `python3 -m invoicer` run as a process from the invoicer folder, as the
accounting team runs it, on .ods files that the tests build."""

from __future__ import annotations

import errno
import os
import pty
import shutil
import subprocess
import sys
import zipfile
from decimal import Decimal

from tests._ods import HEADER, MIMETYPE, Folder

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES = [["Design", 1200, 1], ["Hosting", Decimal("15.5"), 12], ["Domain", Decimal("9.99"), None]]


def environment():
    """The test's environment, without the PYTHON settings that would change what python3 imports."""
    return {name: value for name, value in os.environ.items() if not name.startswith("PYTHON")}


def invoice_row(label, amount):
    """One row of the invoice's text, as render lays it out."""
    return f"{label:<30}{amount:>12} EUR"


# The invoice of LINES at 19 %, its sums counted by hand: 1200 + 15.5 * 12 + 9.99 = 1395.99,
# its tax 265.2381 rounded to 265.24, and its total 1661.23.
INVOICE = "\n".join(
    [
        invoice_row("Design", "1200"),
        invoice_row("Hosting", "186.0"),
        invoice_row("Domain", "9.99"),
        invoice_row("Subtotal", "1395.99"),
        invoice_row("Tax", "265.24"),
        invoice_row("Total", "1661.23"),
    ]
) + "\n"


def command(*arguments, cwd=ROOT, flags=()):
    """Runs `python3 [flags] -m invoicer <arguments>` in cwd, and gives its status, stdout, and stderr."""
    done = subprocess.run(
        [sys.executable, *flags, "-m", "invoicer", *arguments],
        cwd=cwd,
        env=environment(),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return done.returncode, done.stdout, done.stderr


def in_terminal(*arguments):
    """Runs `python3 -m invoicer <arguments>` from the invoicer folder with its stdout a terminal,
    and gives the text the terminal shows, its line ends as the program wrote them."""
    primary, secondary = pty.openpty()
    process = subprocess.Popen(
        [sys.executable, "-m", "invoicer", *arguments], cwd=ROOT, env=environment(), stdout=secondary
    )
    os.close(secondary)
    shown = b""
    while True:
        try:
            chunk = os.read(primary, 4096)
        except OSError as error:  # Linux ends a terminal whose program has ended with EIO.
            if error.errno != errno.EIO:
                raise
            chunk = b""
        if not chunk:
            break
        shown += chunk
    process.wait(timeout=60)
    os.close(primary)
    return shown.decode("utf-8").replace("\r\n", "\n")


class Command(Folder):
    def test_i_s1_a_sheet_of_lines_and_a_rate_give_the_invoice(self):
        """Given a sheet of three lines, one with an empty quantity,
        when `python3 -m invoicer <sheet> --tax-rate 19` runs from the invoicer folder,
        then it writes the invoice with the sums counted by hand to stdout, nothing to stderr, and ends with 0.

        Traces: I-S1, S1, P1, command, sheet reader, render.
        """
        path = self.sheet([HEADER] + LINES)

        self.assertEqual(command(path, "--tax-rate", "19"), (0, INVOICE, ""))

    def test_i_s2_rate_a_rate_that_isnt_a_number_is_refused(self):
        """Given a sheet of three lines,
        when the command runs with --tax-rate nineteen,
        then it writes one line naming --tax-rate to stderr, nothing to stdout, and ends with 2.

        Traces: I-S2-rate, S2, P2, command.
        """
        path = self.sheet([HEADER] + LINES)

        self.assertEqual(
            command(path, "--tax-rate", "nineteen"),
            (2, "", 'invoicer: --tax-rate must be a percent from 0 to 100, such as 19, 7.5, or 19%, not "nineteen"\n'),
        )

    def test_i_s2_rate_a_rate_out_of_range_is_refused(self):
        """Given a sheet of three lines,
        when the command runs with --tax-rate 190,
        then it writes one line naming --tax-rate to stderr, nothing to stdout, and ends with 2.

        Traces: I-S2-rate, S2, P2, command.
        """
        path = self.sheet([HEADER] + LINES)

        self.assertEqual(
            command(path, "--tax-rate", "190"),
            (2, "", 'invoicer: --tax-rate must be a percent from 0 to 100, such as 19, 7.5, or 19%, not "190"\n'),
        )

    def test_i_s2_sheet_a_text_price_is_refused_by_its_row_and_column(self):
        """Given a sheet whose row 3 holds the text `twelve` in its Price column,
        when the command runs on it with --tax-rate 19,
        then it writes one line naming row 3 and the Price column to stderr, nothing to stdout, and ends with 2.

        Traces: I-S2-sheet, S2, P2, command, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 1200, 1], ["Hosting", "twelve", 1]])

        self.assertEqual(
            command(path, "--tax-rate", "19"),
            (
                2,
                "",
                f'invoicer: {path}: first sheet "Sheet1", row 3, column B (Price) holds "twelve", not a number;'
                " enter the price as a number, such as 12.50\n",
            ),
        )

    def test_i_s2_rate_a_rate_written_as_a_fraction_is_refused(self):
        """Given a sheet of three lines,
        when the command runs with --tax-rate 0.19, as if for 19 %,
        then it writes one line telling to write 19 for 19 % to stderr, nothing to stdout, and ends with 2.

        Traces: I-S2-rate, S2, P2, command.
        """
        path = self.sheet([HEADER] + LINES)

        self.assertEqual(
            command(path, "--tax-rate", "0.19"),
            (2, "", 'invoicer: --tax-rate is a percent, so "0.19" would be 0.19 %; write 19 for 19 %\n'),
        )

    def test_i_s2_sheet_a_damaged_file_is_refused_in_one_line(self):
        """Given a file with the .ods mimetype whose content is cut off mid-tag,
        when the command runs on it with --tax-rate 19,
        then it writes one line to save it again from Calc to stderr, no traceback, nothing to stdout, and ends with 2.

        Traces: I-S2-sheet, S2, P2, command, sheet reader.
        """
        path = self.path("damaged.ods")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(zipfile.ZipInfo("mimetype"), MIMETYPE)
            archive.writestr("content.xml", "<office:document-content><office:bo")

        self.assertEqual(
            command(path, "--tax-rate", "19"),
            (2, "", f"invoicer: {path}: can't be read as a Calc spreadsheet; save it again from Calc as .ods\n"),
        )

    def test_i_p1_headers_in_another_order_and_case_with_an_extra_column_give_the_same_invoice(self):
        """Given the three lines under the headers QUANTITY, Notes, price, Description, with a note on a line,
        when the command runs on it with --tax-rate 19,
        then it writes the same invoice as for the sheet laid out Description, Price, Quantity.

        Traces: I-P1, P1, command, sheet reader.
        """
        rows = [["QUANTITY", "Notes", "price", "Description"]] + [
            [quantity, "sent by mail", price, description] for description, price, quantity in LINES
        ]
        path = self.sheet(rows)

        self.assertEqual(command(path, "--tax-rate", "19"), (0, INVOICE, ""))

    def test_i_p3_the_command_runs_with_nothing_installed(self):
        """Given a fresh copy of the invoicer folder, and a sheet of three lines,
        when the command runs from that copy as `python3 -E -s -S -m invoicer`, which reads no
        PYTHON setting and no site-packages, so that only Python's standard library and the folder
        can be imported,
        then it writes the invoice and ends with 0.

        Traces: I-P3, P3, command.
        """
        copy = self.path("invoicer-folder")
        shutil.copytree(os.path.join(ROOT, "invoicer"), os.path.join(copy, "invoicer"), ignore=shutil.ignore_patterns("__pycache__"))
        path = self.sheet([HEADER] + LINES)

        self.assertEqual(command(path, "--tax-rate", "19", cwd=copy, flags=("-E", "-s", "-S")), (0, INVOICE, ""))

    def test_i_print_the_text_written_to_a_pipe_is_the_text_shown_in_the_terminal(self):
        """Given a sheet of three lines,
        when the command runs once with its output in a terminal and once into a pipe, as the
        guide's print step sends it to lp,
        then the pipe gets the same text that the terminal shows.

        Traces: I-print, S1, command.
        """
        path = self.sheet([HEADER] + LINES)

        shown = in_terminal(path, "--tax-rate", "19")

        self.assertEqual(shown, INVOICE, "the terminal shows the invoice")
        self.assertEqual(command(path, "--tax-rate", "19")[1], shown, "the pipe gets what the terminal shows")
