"""The unit cases of the spreadsheet reader, ods.read, on .ods files as LibreOffice Calc saves them.

Each docstring names, after Supports, the integration case of tests/test_integration.py that it
supports.
"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path

import spreadsheet
from spreadsheet import WALKTHROUGH_ROWS, Value

from invoicer import Line, ods
from invoicer.refusal import Refusal

HEADING: list[Value] = ["Description", "Price", "Quantity"]


class ReadTest(unittest.TestCase):
    """ods.read on one file at a time, built in a folder of its own."""

    def setUp(self) -> None:
        """Makes the folder that the file goes in."""
        held = tempfile.TemporaryDirectory()
        self.addCleanup(held.cleanup)
        self.path = os.path.join(held.name, "October.ods")

    def read(self, rows: list[list[Value]]) -> list[Line]:
        """The lines that ods.read gives for a first sheet of `rows`."""
        spreadsheet.write(self.path, rows)
        return ods.read(self.path)

    def refusal(self, rows: list[list[Value]]) -> Refusal:
        """The Refusal that ods.read raises for a first sheet of `rows`."""
        spreadsheet.write(self.path, rows)
        with self.assertRaises(Refusal) as refused:
            ods.read(self.path)
        return refused.exception

    def assert_lines(self, got: list[Line], *expected: tuple) -> None:
        """`got` is one library Line for each of `expected`, each price to the cent."""
        self.assertTrue(all(isinstance(line, Line) for line in got))
        held = [
            (line.description, str(line.price), line.quantity, type(line.quantity))
            for line in got
        ]
        self.assertEqual(held, [(d, p, q, int) for d, p, q in expected])

    def test_the_walkthroughs_rows_give_its_lines(self) -> None:
        """Supports: test_s1_prints_the_walkthrough_invoice.

        Given the walkthrough's October.ods, its prices typed as 85.00, 14.50, and 450.00.
        When ods.read reads it.
        Then it gives the three library Lines, each price a Decimal to the cent and each
        quantity a whole number.
        """
        self.assert_lines(
            self.read([list(row) for row in WALKTHROUGH_ROWS]),
            ("Bookkeeping, October", "85.00", 12),
            ("Payroll, October", "14.50", 9),
            ("Annual accounts 2025", "450.00", 1),
        )

    def test_each_kind_of_cell_that_calc_saves_in_a_line_reads_without_loss(
        self,
    ) -> None:
        """Supports: test_s1_prints_the_walkthrough_invoice.

        Given lines whose price is a currency or a formula, whose quantity is a formula, and
        whose description is in spans or holds an ampersand.
        When ods.read reads them.
        Then each gives its description, price, and quantity as Calc shows them.
        """
        self.assert_lines(
            self.read(
                [
                    HEADING,
                    ["Bookkeeping, October", spreadsheet.currency("85.00"), 12],
                    ["Payroll, October", spreadsheet.formula("14.5", "of:=29/2"), 9],
                    [
                        "Annual accounts 2025",
                        Decimal("450.00"),
                        spreadsheet.formula("1", "of:=3-2"),
                    ],
                    [spreadsheet.spans("Travel, ", "October"), Decimal("0.01"), 1],
                    ["Smith & Co, fees", Decimal("1234567.89"), 1],
                ]
            ),
            ("Bookkeeping, October", "85.00", 12),
            ("Payroll, October", "14.50", 9),
            ("Annual accounts 2025", "450.00", 1),
            ("Travel, October", "0.01", 1),
            ("Smith & Co, fees", "1234567.89", 1),
        )

    def test_the_columns_are_found_by_their_names(self) -> None:
        """Supports: test_s1_reads_the_columns_by_their_names.

        Given row 1 of Quantity, Notes, Price, and Description, in that order.
        When ods.read reads a line under them.
        Then it gives the line, the Notes skipped.
        """
        got = self.read(
            [
                ["Quantity", "Notes", "Price", "Description"],
                [9, "agreed", Decimal("14.50"), "Payroll"],
            ]
        )
        self.assert_lines(got, ("Payroll", "14.50", 9))

    def test_only_the_first_sheet_is_read(self) -> None:
        """Supports: test_s1_reads_only_the_first_sheet.

        Given a first sheet of one line, and a second sheet of another.
        When ods.read reads the file.
        Then it gives the first sheet's line alone.
        """
        spreadsheet.write(
            self.path,
            [HEADING, ["Payroll", Decimal("14.50"), 9]],
            others=[[HEADING, ["Payroll, September", Decimal("14.50"), 8]]],
        )
        self.assert_lines(ods.read(self.path), ("Payroll", "14.50", 9))

    def test_blank_rows_give_no_line(self) -> None:
        """Supports: test_s3_goes_on_as_s1_where_every_row_is_right.

        Given two lines with blank rows between them, and Calc's million blank rows after.
        When ods.read reads the file.
        Then it gives the two lines alone.
        """
        got = self.read(
            [
                HEADING,
                ["A", Decimal("1.00"), 1],
                [None, None, None],
                [None, None, None],
                ["B", Decimal("2.00"), 2],
            ]
        )
        self.assert_lines(got, ("A", "1.00", 1), ("B", "2.00", 2))

    def test_a_thousand_lines_read_in_their_order(self) -> None:
        """Supports: test_s1_sums_are_the_library_sums.

        Given 1000 lines.
        When ods.read reads the file.
        Then it gives the 1000 lines, in the order of their rows.
        """
        rows: list[list[Value]] = [HEADING]
        rows += [[f"Item {n}", Decimal(n).scaleb(-2), n] for n in range(1, 1001)]
        got = self.read(rows)
        self.assertEqual(
            [line.description for line in got], [f"Item {n}" for n in range(1, 1001)]
        )

    def test_the_reader_writes_nothing(self) -> None:
        """Supports: test_s3_names_a_missing_file.

        Given the walkthrough's October.ods, and a path where no file is.
        When ods.read reads each.
        Then the terminal gets nothing, as only the command writes there.
        """
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.read([list(row) for row in WALKTHROUGH_ROWS])
            with self.assertRaises(Refusal):
                ods.read(self.path + ".missing")
        self.assertEqual(out.getvalue() + err.getvalue(), "")

    def test_a_missing_file_is_refused_by_its_name(self) -> None:
        """Supports: test_s3_names_a_missing_file.

        Given a path where no file is.
        When ods.read reads it.
        Then it refuses, naming the path.
        """
        missing = os.path.join(os.path.dirname(self.path), "November.ods")
        with self.assertRaises(Refusal) as refused:
            ods.read(missing)
        self.assertIn(missing, refused.exception.fix)

    def test_a_file_that_isnt_ods_is_refused_by_its_name(self) -> None:
        """Supports: test_s3_names_a_file_that_isnt_ods.

        Given a CSV file, a CSV file renamed to .ods, and a zip file of another kind named .ods.
        When ods.read reads each.
        Then it refuses each, naming its path.
        """
        folder = Path(self.path).parent
        csv = "Description,Price,Quantity\nPayroll,14.50,9\n"
        (folder / "October.csv").write_text(csv, encoding="utf-8")
        (folder / "Renamed.ods").write_text(csv, encoding="utf-8")
        with zipfile.ZipFile(folder / "Other.ods", "w") as archive:
            archive.writestr(
                "mimetype",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        for name in ("October.csv", "Renamed.ods", "Other.ods"):
            with self.subTest(file=name):
                with self.assertRaises(Refusal) as refused:
                    ods.read(str(folder / name))
                self.assertIn(name, refused.exception.fix)

    def test_a_missing_column_is_refused_by_its_name(self) -> None:
        """Supports: test_s3_names_a_missing_column.

        Given a row 1 that lacks Description, Price, or Quantity.
        When ods.read reads the file.
        Then it refuses, naming the column it lacks.
        """
        for missing in ("Description", "Price", "Quantity"):
            with self.subTest(column=missing):
                heading: list[Value] = [
                    name if name != missing else "Notes"
                    for name in ("Description", "Price", "Quantity")
                ]
                refusal = self.refusal([heading, ["Payroll", Decimal("14.50"), 9]])
                self.assertIn(missing, refusal.fix)

    def test_a_price_that_isnt_a_number_is_refused_as_the_readme_shows(self) -> None:
        """Supports: test_s3_names_the_row_of_a_price_that_isnt_a_number.

        Given row 3 holding the price "14,50 EUR" as text.
        When ods.read reads the file.
        Then it refuses with `row 3: the price "14,50 EUR" isn't a number`.
        """
        rows = [list(row) for row in WALKTHROUGH_ROWS]
        rows[2][1] = "14,50 EUR"
        self.assertIn(
            'row 3: the price "14,50 EUR" isn\'t a number', self.refusal(rows).fix
        )

    def test_a_price_that_isnt_to_the_cent_is_refused_by_its_row(self) -> None:
        """Supports: test_s3_names_the_row_of_a_price_that_isnt_a_number.

        Given row 2 with no price, or with a price of 14.505, beyond the cent.
        When ods.read reads the file.
        Then it refuses, naming row 2.
        """
        for price in (None, Decimal("14.505")):
            with self.subTest(price=price):
                self.assertIn(
                    "row 2", self.refusal([HEADING, ["Payroll", price, 9]]).fix
                )

    def test_a_quantity_from_1_reads(self) -> None:
        """Supports: test_s3_names_the_row_of_a_quantity_of_0.

        Given row 2 with a quantity of 1, the least that reads.
        When ods.read reads the file.
        Then it gives the line with a quantity of 1.
        """
        self.assert_lines(
            self.read([HEADING, ["Payroll", Decimal("14.50"), 1]]),
            ("Payroll", "14.50", 1),
        )

    def test_a_quantity_that_isnt_a_whole_number_from_1_is_refused_by_its_row(
        self,
    ) -> None:
        """Supports: test_s3_names_the_row_of_a_quantity_of_0.

        Given row 2 with a quantity of 0, -1, or 2.5, the text one, or none.
        When ods.read reads the file.
        Then it refuses, naming row 2.
        """
        for quantity in (0, -1, Decimal("2.5"), "one", None):
            with self.subTest(quantity=quantity):
                self.assertIn(
                    "row 2",
                    self.refusal(
                        [HEADING, ["Payroll", Decimal("14.50"), quantity]]
                    ).fix,
                )

    def test_a_row_with_no_description_is_refused_by_its_row(self) -> None:
        """Supports: test_s3_names_the_row_with_no_description.

        Given row 2 with a price and a quantity but no description.
        When ods.read reads the file.
        Then it refuses, naming row 2.
        """
        self.assertIn("row 2", self.refusal([HEADING, [None, Decimal("14.50"), 9]]).fix)

    def test_a_first_sheet_with_no_line_is_refused_by_the_files_name(self) -> None:
        """Supports: test_s3_names_the_file_with_no_line.

        Given a first sheet of row 1 alone, or of row 1 and blank rows.
        When ods.read reads the file.
        Then it refuses, naming the file.
        """
        blank: list[Value] = [None, None, None]
        for rows in ([HEADING], [HEADING, blank, blank]):
            with self.subTest(rows=len(rows)):
                self.assertIn("October.ods", self.refusal(rows).fix)

    def test_only_the_first_wrong_row_is_named(self) -> None:
        """Supports: test_s3_names_only_the_first_wrong_row.

        Given rows 2 and 3, each with a quantity of 0.
        When ods.read reads the file.
        Then it refuses, naming row 2 and not row 3.
        """
        refusal = self.refusal(
            [HEADING, ["A", Decimal("1.00"), 0], ["B", Decimal("1.00"), 0]]
        )
        self.assertIn("row 2", refusal.fix)
        self.assertNotIn("row 3", refusal.fix)

    def test_a_row_is_named_by_the_number_calc_shows(self) -> None:
        """Supports: test_s3_counts_rows_as_calc_shows_them.

        Given a line in row 2, blank rows 3 to 6, and a quantity of 0 in row 7.
        When ods.read reads the file.
        Then it refuses, naming row 7.
        """
        blank: list[Value] = [None, None, None]
        rows: list[list[Value]] = [
            HEADING,
            ["A", Decimal("1.00"), 1],
            blank,
            blank,
            blank,
            blank,
        ]
        rows.append(["B", Decimal("1.00"), 0])
        self.assertIn("row 7", self.refusal(rows).fix)


if __name__ == "__main__":
    unittest.main()
