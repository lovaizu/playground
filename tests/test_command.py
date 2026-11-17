"""Tests of the invoicer command, one for each of its cases, run as `invoicer LINES --rate PERCENT`
through invoicer.command.main."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from invoicer.command import main

LINES = "Design;100.00;2\nHosting;10.50;1\n"


def row(label, amount):
    """One row of the printed invoice, in the columns that invoicer.render lays out."""
    return label.ljust(30) + amount.rjust(12) + " EUR"


class CommandTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def saved(self, content, encoding="utf-8"):
        """The path of a file of lines, as the spreadsheet saved it."""
        path = os.path.join(self.folder, "lines.csv")
        with open(path, "wb") as f:
            f.write(content.encode(encoding))
        return path

    def run_command(self, *argv):
        """The exit code, standard output and standard error of `invoicer <argv>`."""
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                main(list(argv))
            except SystemExit as stopped:
                code = stopped.code
        return code, out.getvalue(), err.getvalue()

    def test_prints_the_invoice_of_the_lines_at_the_rate_given(self):
        # Given two lines saved from the spreadsheet, when run at 19 percent, then it prints each
        # line, the subtotal 210.50, the tax 39.995 rounded half up to 40.00, and the total.
        code, out, err = self.run_command(self.saved(LINES), "--rate", "19")

        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            out,
            "\n".join(
                [
                    row("Design", "200.00"),
                    row("Hosting", "10.50"),
                    row("Subtotal", "210.50"),
                    row("Tax", "40.00"),
                    row("Total", "250.50"),
                ]
            )
            + "\n",
        )

    def test_reads_a_rate_written_with_a_percent_sign(self):
        code, out, _ = self.run_command(self.saved(LINES), "--rate", "7.7%")

        self.assertEqual(code, 0)
        self.assertIn(row("Tax", "16.21"), out.splitlines(), "210.50 at 7.7% is 16.2085")

    def test_takes_a_rate_of_zero(self):
        code, out, _ = self.run_command(self.saved(LINES), "--rate", "0")

        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[-2:], [row("Tax", "0.00"), row("Total", "210.50")])

    def test_takes_a_rate_of_a_hundred(self):
        code, out, _ = self.run_command(self.saved(LINES), "--rate", "100")

        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[-2:], [row("Tax", "210.50"), row("Total", "421.00")])

    def test_refuses_a_rate_above_a_hundred(self):
        code, out, err = self.run_command(self.saved(LINES), "--rate", "100.01")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            "invoicer: error: argument --rate: the tax rate must be a percent from 0 to 100, "
            "written with a point, such as 19 or 7.7, not '100.01'",
            err,
        )

    def test_refuses_a_negative_rate(self):
        code, out, err = self.run_command(self.saved(LINES), "--rate=-1")

        self.assertEqual((code, out), (2, ""))
        self.assertIn("not '-1'", err, "the refused rate is named")

    def test_refuses_a_rate_that_is_not_a_number(self):
        code, out, err = self.run_command(self.saved(LINES), "--rate", "7,7")

        self.assertEqual((code, out), (2, ""))
        self.assertIn("not '7,7'", err, "the refused rate is named")

    def test_refuses_a_rate_of_nan(self):
        code, out, err = self.run_command(self.saved(LINES), "--rate", "NaN")

        self.assertEqual((code, out), (2, ""))
        self.assertIn("not 'NaN'", err, "the refused rate is named")

    def test_refuses_a_run_without_a_rate(self):
        code, out, err = self.run_command(self.saved(LINES))

        self.assertEqual((code, out), (2, ""))
        self.assertIn("invoicer: error: the following arguments are required: --rate", err)

    def test_refuses_a_file_that_does_not_exist(self):
        missing = os.path.join(self.folder, "missing.csv")

        code, out, err = self.run_command(missing, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {missing}: no such file; give the path of the file of lines "
            "saved from the spreadsheet",
            err,
        )

    def test_refuses_a_file_not_saved_as_utf8(self):
        path = self.saved("Café;3.00;1\n", encoding="cp1252")

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {path}: not saved as UTF-8 text; save it from the spreadsheet "
            "as CSV UTF-8",
            err,
        )

    def test_reads_lines_saved_with_a_byte_order_mark(self):
        code, out, _ = self.run_command(self.saved(LINES, encoding="utf-8-sig"), "--rate", "19")

        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], row("Design", "200.00"))

    def test_refuses_a_file_with_no_lines(self):
        path = self.saved("\n\n")

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {path}: holds no line; each row must be "
            "<description>;<price>;<quantity>",
            err,
        )

    def test_prints_nothing_when_a_row_is_wrong(self):
        # Given a file whose first rows are right and whose third is wrong, then the command
        # prints nothing, and its message names the file and the row.
        path = self.saved(LINES + "Support;ten;1\n")

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {path}, row 3: the price must be a number written with a point, "
            "such as 12.50, not 'ten'",
            err,
        )


if __name__ == "__main__":
    unittest.main()
