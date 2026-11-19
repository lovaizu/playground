"""The integration cases: the joined parts, run through the command as in the terminal.

Each case builds a real .ods file in a folder of its own and puts the stand-in lp first on the
path. Its docstring names, after Supports, the elements of docs/architecture.md that it shows.
"""

from __future__ import annotations

import ast
import importlib.util
import random
import re
import sysconfig
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

import spreadsheet
from harness import ROOT, Folder
from spreadsheet import SENT, WALKTHROUGH_ARGS, WALKTHROUGH_INVOICE, WALKTHROUGH_ROWS

import invoicer
from invoicer import Line, render, subtotal, tax_of, total

TODAY_LINE = "Date: {}"


def walkthrough_invoice() -> str:
    """The walkthrough's invoice as the terminal shows it, dated today."""
    return WALKTHROUGH_INVOICE.format(today=date.today().isoformat())


class Refusals(Folder):
    """What every refusal of a run gives: status 1, the names to fix, and nothing printed."""

    def assert_refused(self, code: int, out: str, err: str, *names: str) -> None:
        """The run ended with 1, named each of `names`, and showed and printed no invoice."""
        said = out + err
        self.assertEqual(code, 1, said)
        for name in names:
            self.assertIn(name, said)
        self.assertNotIn("Subtotal", said)
        self.assertEqual(self.jobs(), [])


class S1Test(Folder):
    """S1: a client's invoice on paper."""

    def test_s1_prints_the_walkthrough_invoice(self) -> None:
        """Supports: S1, P1.1, P2.1, P2.3, Spreadsheet, Details, Invoice, command, spreadsheet reader, invoice, printer, library.

        Given the walkthrough's October.ods, and a default printer that takes the job.
        When the run asks for invoice 2026-031 for Nordwind GmbH at --rate 19.
        Then the terminal shows the walkthrough's invoice, dated today, then that it went to the
        default printer, lp gets the same invoice, and the run ends with 0.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        code, out, err = self.invoicer(WALKTHROUGH_ARGS)
        self.assertEqual(out.rstrip("\n"), f"{walkthrough_invoice()}\n\n{SENT}", err)
        self.assertEqual(
            [job["input"].rstrip("\n") for job in self.jobs()], [walkthrough_invoice()]
        )
        self.assertEqual(code, 0)

    def test_s1_sends_to_the_default_printer_with_none_named(self) -> None:
        """Supports: S1, P5.3, printer.

        Given the walkthrough's October.ods.
        When the run prints its invoice.
        Then lp runs once, with no printer named, so the default printer takes the job.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        self.invoicer(WALKTHROUGH_ARGS)
        jobs = self.jobs()
        self.assertEqual(len(jobs), 1)
        self.assertFalse(
            [arg for arg in jobs[0]["args"] if arg.startswith(("-d", "-P"))]
        )

    def test_s1_names_cups_client_where_lp_is_missing(self) -> None:
        """Supports: S1, P5.3, P3.3, printer, Refusal.

        Given the walkthrough's October.ods, and no lp on the path.
        When the run asks for the walkthrough's invoice.
        Then the terminal shows the invoice, then the reason naming cups-client to install, and
        the run ends with 1.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        self.without_lp()
        code, out, err = self.invoicer(WALKTHROUGH_ARGS)
        self.assertIn(walkthrough_invoice(), out)
        self.assertIn("cups-client", out + err)
        self.assertNotIn(SENT, out + err)
        self.assertEqual(code, 1)

    def test_s1_names_lpstat_where_no_default_printer_is_set(self) -> None:
        """Supports: S1, P5.3, P3.3, printer, Refusal.

        Given the walkthrough's October.ods, and CUPS with no default printer set.
        When the run asks for the walkthrough's invoice.
        Then the terminal shows the invoice, then the reason with `lpstat -d` to check, and the
        run ends with 1.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        self.printer_answers("no-default")
        code, out, err = self.invoicer(WALKTHROUGH_ARGS)
        self.assertIn(walkthrough_invoice(), out)
        self.assertIn("lpstat -d", out + err)
        self.assertNotIn(SENT, out + err)
        self.assertEqual(code, 1)

    def test_s1_gives_the_reason_where_the_printer_refuses(self) -> None:
        """Supports: S1, P5.3, P3.3, printer, Refusal.

        Given the walkthrough's October.ods, and a default printer that refuses the job.
        When the run asks for the walkthrough's invoice.
        Then the terminal shows the invoice, then CUPS's own reason, and the run ends with 1.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        self.printer_answers("refuses")
        code, out, err = self.invoicer(WALKTHROUGH_ARGS)
        self.assertIn(walkthrough_invoice(), out)
        self.assertIn('Destination "Office" is not accepting jobs', out + err)
        self.assertNotIn(SENT, out + err)
        self.assertEqual(code, 1)

    def test_s1_taxes_at_the_typed_rate(self) -> None:
        """Supports: S1, P4.1, Details, command.

        Given the walkthrough's October.ods.
        When the run asks for its invoice at --rate 7.
        Then the invoice shows `Tax rate: 7%` and a tax of 112.04 EUR, at 7 percent and never at
        700, and a total of 1712.54 EUR.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        code, out, _ = self.invoicer(
            [
                "October.ods",
                "--client",
                "Kauri Ltd",
                "--number",
                "2026-032",
                "--rate",
                "7",
            ]
        )
        self.assertIn("Tax rate: 7%\n", out)
        self.assertIn(f"{'Tax':<30}{'112.04':>12} EUR", out)
        self.assertIn(f"{'Total':<30}{'1712.54':>12} EUR", out)
        self.assertEqual(code, 0)

    def test_s1_sums_are_the_library_sums(self) -> None:
        """Supports: S1, P4.1, Line, library.

        Given 40 sheets of 1 to 30 lines each, and rates in percent from 0 to 100.
        When the run asks for each sheet's invoice.
        Then each invoice's rows and sums are those that the library renders for the same lines
        at the rate as a fraction.
        """
        draw = random.Random(140)
        for each in range(40):
            lines = [
                Line(
                    f"Item {n}",
                    Decimal(draw.randint(1, 500000)).scaleb(-2),
                    draw.randint(1, 60),
                )
                for n in range(draw.randint(1, 30))
            ]
            typed = draw.choice(
                ["0", "100", str(draw.randint(0, 100)), f"{draw.randint(0, 99)}.5"]
            )
            rows = [["Description", "Price", "Quantity"]]
            rows += [[line.description, line.price, line.quantity] for line in lines]
            spreadsheet.write(f"sheet{each}.ods", rows)
            argv = [
                f"sheet{each}.ods",
                "--client",
                "Kauri Ltd",
                "--number",
                str(each),
                "--rate",
                typed,
            ]
            code, out, err = self.invoicer(argv)
            with self.subTest(sheet=each, rate=typed):
                self.assertIn(render(lines, Decimal(typed) / 100), out, err)
                self.assertIn(f"Tax rate: {typed}%\n", out)
                self.assertEqual(code, 0)

    def test_s1_keeps_nothing_of_one_invoice_for_the_next(self) -> None:
        """Supports: S1, P2.2, Details.

        Given the walkthrough's October.ods.
        When one run asks for Nordwind GmbH's invoice at 19, then another for Kauri Ltd's at 7.
        Then the second invoice shows only Kauri Ltd, its own number, and its own rate.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        self.invoicer(WALKTHROUGH_ARGS)
        _, out, _ = self.invoicer(
            [
                "October.ods",
                "--client",
                "Kauri Ltd",
                "--number",
                "2026-032",
                "--rate",
                "7",
            ]
        )
        self.assertIn("Client: Kauri Ltd\n", out)
        self.assertIn("Invoice 2026-032\n", out)
        self.assertIn("Tax rate: 7%\n", out)
        for earlier in ("Nordwind", "2026-031", "19%", "304.10"):
            self.assertNotIn(earlier, out)

    def test_s1_reads_the_columns_by_their_names(self) -> None:
        """Supports: S1, P1.2, spreadsheet reader.

        Given a first sheet whose columns are Quantity, Notes, Description, Price, and Amount, a
        formula, holding the walkthrough's lines.
        When the run asks for the walkthrough's invoice.
        Then the invoice is the walkthrough's, the other columns skipped.
        """
        rows: list[list[spreadsheet.Value]] = [
            ["Quantity", "Notes", "Description", "Price", "Amount"]
        ]
        for description, price, quantity in WALKTHROUGH_ROWS[1:]:
            amount = str(Decimal(str(price)) * Decimal(str(quantity)))
            rows.append(
                [
                    quantity,
                    "agreed",
                    description,
                    price,
                    spreadsheet.formula(amount, "of:=[.A2]*[.D2]"),
                ]
            )
        spreadsheet.write("October.ods", rows)
        code, out, err = self.invoicer(WALKTHROUGH_ARGS)
        self.assertEqual(out.rstrip("\n"), f"{walkthrough_invoice()}\n\n{SENT}", err)
        self.assertEqual(code, 0)

    def test_s1_reads_only_the_first_sheet(self) -> None:
        """Supports: S1, P1.2, spreadsheet reader.

        Given the walkthrough's lines on the first sheet, and other lines on a second.
        When the run asks for the walkthrough's invoice.
        Then the invoice holds the first sheet's lines alone.
        """
        other: list[list[spreadsheet.Value]] = [
            ["Description", "Price", "Quantity"],
            ["Payroll, September", Decimal("14.50"), 8],
        ]
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS, others=[other])
        code, out, err = self.invoicer(WALKTHROUGH_ARGS)
        self.assertEqual(out.rstrip("\n"), f"{walkthrough_invoice()}\n\n{SENT}", err)
        self.assertEqual(code, 0)


class S2Test(Folder):
    """S2: the sample invoice after setting up."""

    def assert_sample_shown(self, out: str) -> None:
        """The terminal shows the sample invoice of 119.00 EUR, dated today."""
        self.assertIn(TODAY_LINE.format(date.today().isoformat()), out)
        self.assertRegex(out, re.compile(r"^Total +119\.00 EUR$", re.MULTILINE))

    def test_s2_prints_the_sample(self) -> None:
        """Supports: S2, P5.2, Sample, command, invoice, printer, library.

        Given a folder with no spreadsheet, and a default printer that takes the job.
        When the run asks for `invoicer --sample`.
        Then the terminal shows the sample invoice of 119.00 EUR dated today, then that it went
        to the default printer, lp gets the same invoice, and the run ends with 0.
        """
        code, out, err = self.invoicer(["--sample"])
        self.assert_sample_shown(out)
        self.assertTrue(out.rstrip("\n").endswith(f"\n\n{SENT}"), out + err)
        invoice = out.rstrip("\n")[: -len(SENT)].rstrip("\n")
        self.assertEqual([job["input"].rstrip("\n") for job in self.jobs()], [invoice])
        self.assertEqual(code, 0)

    def test_s2_names_cups_client_where_lp_is_missing(self) -> None:
        """Supports: S2, P5.3, P3.3, printer, Refusal.

        Given no lp on the path.
        When the run asks for `invoicer --sample`.
        Then the terminal shows the sample, then the reason naming cups-client to install, and
        the run ends with 1.
        """
        self.without_lp()
        code, out, err = self.invoicer(["--sample"])
        self.assert_sample_shown(out)
        self.assertIn("cups-client", out + err)
        self.assertEqual(code, 1)

    def test_s2_names_lpstat_where_no_default_printer_is_set(self) -> None:
        """Supports: S2, P5.3, P3.3, printer, Refusal.

        Given CUPS with no default printer set.
        When the run asks for `invoicer --sample`.
        Then the terminal shows the sample, then the reason with `lpstat -d` to check, and the
        run ends with 1.
        """
        self.printer_answers("no-default")
        code, out, err = self.invoicer(["--sample"])
        self.assert_sample_shown(out)
        self.assertIn("lpstat -d", out + err)
        self.assertEqual(code, 1)

    def test_s2_gives_the_reason_where_the_printer_refuses(self) -> None:
        """Supports: S2, P5.3, P3.3, printer, Refusal.

        Given a default printer that refuses the job.
        When the run asks for `invoicer --sample`.
        Then the terminal shows the sample, then CUPS's own reason, and the run ends with 1.
        """
        self.printer_answers("refuses")
        code, out, err = self.invoicer(["--sample"])
        self.assert_sample_shown(out)
        self.assertIn('Destination "Office" is not accepting jobs', out + err)
        self.assertEqual(code, 1)


class S3Test(Refusals):
    """S3: what to fix, with nothing printed."""

    def test_s3_names_the_file_where_none_and_no_sample_are_given(self) -> None:
        """Supports: S3, P5.2, P3.2, P3.3, command, Refusal.

        Given a folder with no spreadsheet.
        When the run is `invoicer` alone.
        Then it names the .ods file it needs, prints no sample, and ends with 1.
        """
        self.assert_refused(*self.invoicer([]), ".ods")

    def test_s3_names_the_file_to_leave_out_beside_sample(self) -> None:
        """Supports: S3, P5.2, P3.2, P3.3, command, Refusal.

        Given the walkthrough's October.ods.
        When the run is `invoicer --sample October.ods`.
        Then it names October.ods to leave out, prints nothing, and ends with 1.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        self.assert_refused(*self.invoicer(["--sample", "October.ods"]), "October.ods")

    def test_s3_names_the_value_to_leave_out_beside_sample(self) -> None:
        """Supports: S3, P5.2, P3.2, P3.3, command, Refusal.

        Given a folder with no spreadsheet.
        When the run is `invoicer --sample --rate 19`.
        Then it names --rate to leave out, prints nothing, and ends with 1.
        """
        self.assert_refused(*self.invoicer(["--sample", "--rate", "19"]), "--rate")

    def test_s3_names_an_empty_client(self) -> None:
        """Supports: S3, P2.1, P3.1, P3.2, P3.3, command, Details, Refusal.

        Given the walkthrough's October.ods.
        When the run gives --client "".
        Then it names --client to fix, prints nothing, and ends with 1.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        argv = ["October.ods", "--client", "", "--number", "2026-031", "--rate", "19"]
        self.assert_refused(*self.invoicer(argv), "--client")

    def test_s3_names_an_empty_number(self) -> None:
        """Supports: S3, P2.1, P3.1, P3.2, P3.3, command, Details, Refusal.

        Given the walkthrough's October.ods.
        When the run gives --number "".
        Then it names --number to fix, prints nothing, and ends with 1.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        argv = [
            "October.ods",
            "--client",
            "Nordwind GmbH",
            "--number",
            "",
            "--rate",
            "19",
        ]
        self.assert_refused(*self.invoicer(argv), "--number")

    def test_s3_names_a_rate_beyond_100(self) -> None:
        """Supports: S3, P2.1, P3.1, P3.2, P3.3, command, Details, Refusal.

        Given the walkthrough's October.ods.
        When the run gives --rate 119, a 19 typed with one key too many.
        Then it names --rate to fix, prints nothing, and ends with 1.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS)
        argv = [
            "October.ods",
            "--client",
            "Nordwind GmbH",
            "--number",
            "2026-031",
            "--rate",
            "119",
        ]
        self.assert_refused(*self.invoicer(argv), "--rate")

    def test_s3_names_the_value_before_reading_the_file(self) -> None:
        """Supports: S3, P3.1, command.

        Given a folder where November.ods is missing.
        When the run gives --client "" for November.ods.
        Then it names --client, and not the missing file, as it checks the values first.
        """
        argv = ["November.ods", "--client", "", "--number", "2026-031", "--rate", "19"]
        code, out, err = self.invoicer(argv)
        self.assert_refused(code, out, err, "--client")
        self.assertNotIn("November.ods", out + err)

    def test_s3_names_a_missing_file(self) -> None:
        """Supports: S3, P3.2, P3.3, spreadsheet reader, Refusal.

        Given a folder where October.ods is missing.
        When the run asks for the walkthrough's invoice.
        Then it names October.ods, prints nothing, and ends with 1.
        """
        self.assert_refused(*self.invoicer(WALKTHROUGH_ARGS), "October.ods")

    def test_s3_names_a_file_that_isnt_ods(self) -> None:
        """Supports: S3, P1.1, P3.2, P3.3, spreadsheet reader, Refusal.

        Given October.csv, the walkthrough's lines saved as CSV.
        When the run asks for its invoice.
        Then it names October.csv, prints nothing, and ends with 1.
        """
        Path("October.csv").write_text(
            "Description,Price,Quantity\nBookkeeping October,85.00,12\n",
            encoding="utf-8",
        )
        argv = ["October.csv"] + WALKTHROUGH_ARGS[1:]
        self.assert_refused(*self.invoicer(argv), "October.csv")

    def test_s3_names_a_missing_column(self) -> None:
        """Supports: S3, P1.2, P3.2, P3.3, spreadsheet reader, Refusal.

        Given October.ods whose row 1 says Cost in place of Price.
        When the run asks for its invoice.
        Then it names the column Price, prints nothing, and ends with 1.
        """
        heading: list[spreadsheet.Value] = ["Description", "Cost", "Quantity"]
        spreadsheet.write("October.ods", [heading] + WALKTHROUGH_ROWS[1:])
        self.assert_refused(*self.invoicer(WALKTHROUGH_ARGS), "Price")

    def test_s3_names_the_row_of_a_price_that_isnt_a_number(self) -> None:
        """Supports: S3, P3.2, P3.3, spreadsheet reader, Refusal.

        Given October.ods whose row 3 holds the price "14,50 EUR" as text.
        When the run asks for its invoice.
        Then it says `row 3: the price "14,50 EUR" isn't a number`, as the README shows, prints
        nothing, and ends with 1.
        """
        rows = [list(row) for row in WALKTHROUGH_ROWS]
        rows[2][1] = "14,50 EUR"
        spreadsheet.write("October.ods", rows)
        self.assert_refused(
            *self.invoicer(WALKTHROUGH_ARGS),
            'row 3: the price "14,50 EUR" isn\'t a number',
        )

    def test_s3_names_the_row_of_a_quantity_of_0(self) -> None:
        """Supports: S3, P3.2, P3.3, spreadsheet reader, Refusal.

        Given October.ods whose row 2 holds a quantity of 0.
        When the run asks for its invoice.
        Then it names row 2, prints nothing, and ends with 1.
        """
        rows = [list(row) for row in WALKTHROUGH_ROWS]
        rows[1][2] = 0
        spreadsheet.write("October.ods", rows)
        self.assert_refused(*self.invoicer(WALKTHROUGH_ARGS), "row 2")

    def test_s3_names_the_row_with_no_description(self) -> None:
        """Supports: S3, P3.2, P3.3, spreadsheet reader, Refusal.

        Given October.ods whose row 4 holds a price and a quantity but no description.
        When the run asks for its invoice.
        Then it names row 4, prints nothing, and ends with 1.
        """
        rows = [list(row) for row in WALKTHROUGH_ROWS]
        rows[3][0] = None
        spreadsheet.write("October.ods", rows)
        self.assert_refused(*self.invoicer(WALKTHROUGH_ARGS), "row 4")

    def test_s3_names_the_file_with_no_line(self) -> None:
        """Supports: S3, P3.1, P3.3, spreadsheet reader, Refusal.

        Given October.ods whose first sheet holds row 1 alone.
        When the run asks for its invoice.
        Then it names October.ods, prints no empty invoice, and ends with 1.
        """
        spreadsheet.write("October.ods", WALKTHROUGH_ROWS[:1])
        self.assert_refused(*self.invoicer(WALKTHROUGH_ARGS), "October.ods")

    def test_s3_names_only_the_first_wrong_row(self) -> None:
        """Supports: S3, P3.2, Refusal.

        Given October.ods whose rows 3 and 4 both hold a quantity of 0.
        When the run asks for its invoice.
        Then it names row 3 alone, so one from accounting fixes one cell and runs it again.
        """
        rows = [list(row) for row in WALKTHROUGH_ROWS]
        rows[2][2] = 0
        rows[3][2] = 0
        spreadsheet.write("October.ods", rows)
        code, out, err = self.invoicer(WALKTHROUGH_ARGS)
        self.assert_refused(code, out, err, "row 3")
        self.assertNotIn("row 4", out + err)

    def test_s3_checks_the_last_row_before_anything_prints(self) -> None:
        """Supports: S3, P3.1, spreadsheet reader.

        Given October.ods whose rows 2 and 3 are right and whose row 4 holds the text one as its quantity.
        When the run asks for its invoice.
        Then it names row 4, and neither the terminal nor lp gets any line of the invoice.
        """
        rows = [list(row) for row in WALKTHROUGH_ROWS]
        rows[3][2] = "one"
        spreadsheet.write("October.ods", rows)
        code, out, err = self.invoicer(WALKTHROUGH_ARGS)
        self.assert_refused(code, out, err, "row 4")
        self.assertNotIn("Bookkeeping, October", out + err)

    def test_s3_counts_rows_as_calc_shows_them(self) -> None:
        """Supports: S3, P3.2, spreadsheet reader.

        Given October.ods with blank rows 3 to 5, and a quantity of 0 in row 7.
        When the run asks for its invoice.
        Then it names row 7, the number that Calc shows beside it.
        """
        rows = [list(row) for row in WALKTHROUGH_ROWS[:2]] + [[None, None, None]] * 3
        rows += [list(row) for row in WALKTHROUGH_ROWS[2:]]
        rows[6][2] = 0
        spreadsheet.write("October.ods", rows)
        self.assert_refused(*self.invoicer(WALKTHROUGH_ARGS), "row 7")

    def test_s3_goes_on_as_s1_where_every_row_is_right(self) -> None:
        """Supports: S3, S1, P3.1, spreadsheet reader.

        Given October.ods holding the walkthrough's lines with a blank row between each.
        When the run asks for its invoice.
        Then every row is right, the blank rows cost nothing, and the walkthrough's invoice
        shows and prints.
        """
        rows: list[list[spreadsheet.Value]] = [list(WALKTHROUGH_ROWS[0])]
        for row in WALKTHROUGH_ROWS[1:]:
            rows += [[None, None, None], list(row)]
        spreadsheet.write("October.ods", rows)
        code, out, err = self.invoicer(WALKTHROUGH_ARGS)
        self.assertEqual(out.rstrip("\n"), f"{walkthrough_invoice()}\n\n{SENT}", err)
        self.assertEqual(len(self.jobs()), 1)
        self.assertEqual(code, 0)


class S4Test(unittest.TestCase):
    """S4: the sums and text in their own code."""

    def test_s4_gives_the_sums_and_text_of_1_4_0(self) -> None:
        """Supports: S4, P4.2, Line, library.

        Given the walkthrough's three lines as the library's Line.
        When code hands them to the library at the rate 0.19.
        Then it gets invoicer 1.4.0's subtotal 1600.50, tax 304.10, total 1904.60, and text.
        """
        lines = [Line(*row) for row in WALKTHROUGH_ROWS[1:]]
        rate = Decimal("0.19")
        self.assertEqual(str(subtotal(lines)), "1600.50")
        self.assertEqual(str(tax_of(subtotal(lines), rate)), "304.10")
        self.assertEqual(str(total(lines, rate)), "1904.60")
        rows = walkthrough_invoice().split("\n\n", 1)[1]
        self.assertEqual(render(lines, rate), rows)

    def test_s4_keeps_the_public_calls(self) -> None:
        """Supports: S4, P4.2, library.

        Given the invoicer package.
        When code imports it.
        Then its public calls are those of 1.4.0, and no more.
        """
        self.assertEqual(
            sorted(invoicer.__all__),
            ["Line", "parse_lines", "render", "subtotal", "tax_of", "total"],
        )


class PrinciplesTest(unittest.TestCase):
    """The principle items that no sequence shows alone."""

    def test_p5_1_needs_nothing_beyond_the_standard_library(self) -> None:
        """Supports: P5.1, command, spreadsheet reader, invoice, printer, library.

        Given the package's pyproject.toml and each module of invoicer.
        When it's read.
        Then it declares no dependency, and each module imports only Python's standard library
        and invoicer.
        """
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertRegex(project, re.compile(r"^dependencies = \[\]$", re.MULTILINE))
        stdlib = sysconfig.get_paths()["stdlib"]
        for name in sorted(_imported(ROOT / "invoicer")):
            with self.subTest(module=name):
                if name == "invoicer":
                    continue
                spec = importlib.util.find_spec(name)
                self.assertIsNotNone(spec)
                assert spec is not None
                origin = spec.origin or ""
                self.assertTrue(
                    origin in ("built-in", "frozen") or origin.startswith(stdlib),
                    origin,
                )

    def test_p4_2_new_parts_call_the_library_only_through_its_public_calls(
        self,
    ) -> None:
        """Supports: P4.2, command, spreadsheet reader, invoice, printer.

        Given the new parts cli.py, ods.py, invoice.py, printer.py, and refusal.py.
        When their imports are read.
        Then each name they take from the library is one of its public calls.
        """
        library = {
            "invoicer",
            "invoicer.lines",
            "invoicer.tax",
            "invoicer.totals",
            "invoicer.render",
        }
        parts = {"cli", "ods", "invoice", "printer", "refusal"}
        for part in sorted(parts):
            tree = ast.parse(
                (ROOT / "invoicer" / f"{part}.py").read_text(encoding="utf-8")
            )
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in library:
                    for alias in node.names:
                        with self.subTest(part=part, name=alias.name):
                            self.assertIn(alias.name, set(invoicer.__all__) | parts)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name, library - {"invoicer"})


def _imported(package: Path) -> set:
    """The top-level name of each module that the package's modules import."""
    found = set()
    for path in package.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return found


if __name__ == "__main__":
    unittest.main()
