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

    def test_prints_each_amount_to_the_cent(self):
        # Given prices saved without two decimals, then each amount shows its cents, 12.345 times
        # 3 is 37.035 rounded half up to 37.04, and the subtotal 226.54 at 19 percent gives the
        # tax 43.0426 rounded to 43.04.
        path = self.saved("Design;89.5;1\nHosting;100;1\nSupport;12.345;3\n")

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            out,
            "\n".join(
                [
                    row("Design", "89.50"),
                    row("Hosting", "100.00"),
                    row("Support", "37.04"),
                    row("Subtotal", "226.54"),
                    row("Tax", "43.04"),
                    row("Total", "269.58"),
                ]
            )
            + "\n",
        )

    def test_prints_a_subtotal_that_adds_up_the_amounts_as_printed(self):
        # Given three lines of 0.005 each, each printed as 0.01, then the subtotal is 0.03, not
        # the 0.015 of the unrounded amounts.
        path = self.saved("Pen;0.005;1\nPencil;0.005;1\nEraser;0.005;1\n")

        code, out, _ = self.run_command(path, "--rate", "0")

        self.assertEqual(code, 0)
        self.assertEqual(
            out.splitlines()[-3:],
            [row("Subtotal", "0.03"), row("Tax", "0.00"), row("Total", "0.03")],
        )

    def test_prints_a_credit_line(self):
        # Given a discount at a negative price, a returned item at a negative quantity, and a
        # cancelled line of quantity 0, then each is printed and counted in the subtotal 169.50,
        # whose tax at 19 percent is 32.205 rounded half up to 32.21.
        path = self.saved(
            "Design;100.00;2\nDiscount;-20.00;1\nReturned hosting;10.50;-1\nCancelled;50.00;0\n"
        )

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            out,
            "\n".join(
                [
                    row("Design", "200.00"),
                    row("Discount", "-20.00"),
                    row("Returned hosting", "-10.50"),
                    row("Cancelled", "0.00"),
                    row("Subtotal", "169.50"),
                    row("Tax", "32.21"),
                    row("Total", "201.71"),
                ]
            )
            + "\n",
        )

    def test_prints_a_description_saved_in_quotes_as_typed(self):
        # Given the cell `Design "Pro"`, which the spreadsheet saves in quotes with its quotes
        # doubled, then the invoice shows it as typed.
        path = self.saved('"Design ""Pro""";100.00;2\n')

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines()[0], row('Design "Pro"', "200.00"))

    def test_prints_a_description_holding_a_semicolon(self):
        # Given a cell typed as Design; phase 1, which the spreadsheet saves in quotes, then the
        # row gives one line of three fields, and the invoice shows the cell as typed.
        path = self.saved('"Design; phase 1";100.00;2\n')

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines()[0], row("Design; phase 1", "200.00"))

    def test_skips_a_row_whose_cells_are_all_empty(self):
        # Given an empty row, which the spreadsheet saves as ;;, between two lines, then the
        # invoice is that of the two lines.
        path = self.saved("Design;100.00;2\n;;\nHosting;10.50;1\n")

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            out.splitlines(),
            [
                row("Design", "200.00"),
                row("Hosting", "10.50"),
                row("Subtotal", "210.50"),
                row("Tax", "40.00"),
                row("Total", "250.50"),
            ],
        )

    def test_refuses_a_heading_row_asking_to_leave_it_out(self):
        path = self.saved("Description;Price;Quantity\n" + LINES)

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {path}, row 1: a heading, as neither its price 'Price' nor its "
            "quantity 'Quantity' is a number; save the lines without the heading row",
            err,
        )

    def test_refuses_a_row_with_an_empty_description(self):
        path = self.saved(LINES + ";5.00;1\n")

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {path}, row 3: the description is empty; write what the line is "
            "for, as the client reads it on the invoice",
            err,
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

    def test_takes_a_rate_of_one(self):
        code, out, _ = self.run_command(self.saved(LINES), "--rate", "1")

        self.assertEqual(code, 0)
        self.assertIn(row("Tax", "2.11"), out.splitlines(), "210.50 at 1% is 2.105")

    def test_refuses_a_rate_below_one_as_a_fraction(self):
        # Given --rate 0.19, meant as 19%, then the command prints no invoice with 0.19% of tax,
        # and asks for the percent.
        code, out, err = self.run_command(self.saved(LINES), "--rate", "0.19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            "invoicer: error: argument --rate: the tax rate must be 0 or a percent from 1 to "
            "100, as a rate between 0 and 1 may be meant as a fraction; write the percent, "
            "such as 19 for 19%, not '0.19'",
            err,
        )

    def test_refuses_a_rate_below_one_written_with_a_percent_sign(self):
        code, out, err = self.run_command(self.saved(LINES), "--rate", "0.5%")

        self.assertEqual((code, out), (2, ""))
        self.assertIn("not '0.5%'", err, "the refused rate is named")

    def test_takes_a_rate_of_zero_written_with_a_percent_sign(self):
        code, out, _ = self.run_command(self.saved(LINES), "--rate", "0%")

        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[-2:], [row("Tax", "0.00"), row("Total", "210.50")])

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

    def test_refuses_a_folder_in_place_of_the_file(self):
        code, out, err = self.run_command(self.folder, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {self.folder}: is a folder; give the path of the file of lines "
            "saved from the spreadsheet",
            err,
        )

    @unittest.skipIf(
        hasattr(os, "geteuid") and os.geteuid() == 0, "root reads a file whatever its permissions"
    )
    def test_refuses_a_file_that_cannot_be_read(self):
        path = self.saved(LINES)
        os.chmod(path, 0)

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {path}: no permission to read it; save it again from the "
            "spreadsheet in a folder of your own",
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

    def test_refuses_a_row_of_more_than_three_fields(self):
        path = self.saved("Design;100.00;2;paid\n")

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {path}, row 1: a row must be <description>;<price>;<quantity>, "
            "three fields, not 4: 'Design;100.00;2;paid'",
            err,
        )

    def test_refuses_a_price_too_large_to_print(self):
        path = self.saved("Design;1e400;1\n")

        code, out, err = self.run_command(path, "--rate", "19")

        self.assertEqual((code, out), (2, ""))
        self.assertIn(
            f"invoicer: error: {path}, row 1: the price must be between -1000000000 and "
            "1000000000, not '1e400'",
            err,
        )


if __name__ == "__main__":
    unittest.main()
