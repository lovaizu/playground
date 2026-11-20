"""The unit cases of read_lines, the sheet reader."""

from __future__ import annotations

import zipfile
from decimal import Decimal

from invoicer.sheet import SheetError, read_lines
from tests._ods import HEADER, MIMETYPE, Currency, Folder, table, write_tables


def found(lines):
    """Each line as (description, price, quantity), so a whole list compares at once."""
    return [(line.description, line.price, line.quantity) for line in lines]


class ReadLines(Folder):
    def test_read_lines_gives_each_line_of_a_typical_sheet_in_sheet_order(self):
        """Given a sheet with the header Description, Price, Quantity and three lines,
        when read_lines reads it,
        then it gives the three lines in sheet order, each price a Decimal and each quantity an int.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 1200, 1], ["Hosting", Decimal("15.5"), 12], ["Domain", Decimal("9.99"), 3]])

        lines = read_lines(path)

        self.assertEqual(
            found(lines),
            [("Design", Decimal("1200"), 1), ("Hosting", Decimal("15.5"), 12), ("Domain", Decimal("9.99"), 3)],
        )
        self.assertEqual([type(line.price) for line in lines], [Decimal] * 3, "each price is a Decimal")
        self.assertEqual([type(line.quantity) for line in lines], [int] * 3, "each quantity is an int")

    def test_read_lines_finds_headers_in_any_order_and_letter_case_and_ignores_other_columns(self):
        """Given a header row Quantity, Notes, PRICE, description, and a line under it,
        when read_lines reads it,
        then the line takes its description, price, and quantity from their columns, and the note is left out.

        Traces: U-read_lines, P1, sheet reader.
        """
        path = self.sheet([["Quantity", "Notes", "PRICE", "description"], [2, "paid early", 50, "Design"]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("50"), 2)])

    def test_read_lines_reads_only_the_first_sheet(self):
        """Given a file of two sheets, the first with one line and the second with another,
        when read_lines reads it,
        then it gives only the first sheet's line.

        Traces: U-read_lines, P1, sheet reader.
        """
        first = table([HEADER, ["Design", 100, 1]], "Invoice")
        second = table([HEADER, ["Hosting", 5, 1]], "Notes")
        path = write_tables(self.path("two.ods"), first + second)

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("100"), 1)])

    def test_read_lines_expands_repeated_rows_and_columns_of_the_ods_format(self):
        """Given a sheet as Calc saves it, with two empty columns written as one repeated cell
        between Description and Price, a line written as one row repeated twice, and the sheet's
        empty rows to its end written as one repeated row,
        when read_lines reads it,
        then it gives the repeated line twice and finds the price past the repeated columns.

        Traces: U-read_lines, P1, sheet reader.
        """
        path = self.sheet(
            [
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Description</text:p></table:table-cell>'
                    '<table:table-cell table:number-columns-repeated="2"/>'
                    '<table:table-cell office:value-type="string"><text:p>Price</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
                (
                    '<table:table-row table:number-rows-repeated="2">'
                    '<table:table-cell office:value-type="string"><text:p>Hosting</text:p></table:table-cell>'
                    '<table:table-cell table:number-columns-repeated="2"/>'
                    '<table:table-cell office:value-type="float" office:value="15.5"><text:p>15.5</text:p></table:table-cell>'
                    '<table:table-cell table:number-columns-repeated="16380"/>'
                    "</table:table-row>"
                ),
                (
                    '<table:table-row table:number-rows-repeated="1048573">'
                    '<table:table-cell table:number-columns-repeated="16384"/>'
                    "</table:table-row>"
                ),
            ],
            "repeated.ods",
        )

        self.assertEqual(found(read_lines(path)), [("Hosting", Decimal("15.5"), 1), ("Hosting", Decimal("15.5"), 1)])

    def test_read_lines_names_the_column_letter_past_repeated_columns(self):
        """Given a sheet whose Price column is D, past two empty columns written as one repeated
        cell, and whose row 2 holds text there,
        when read_lines reads it,
        then the refusal names row 2 and column D.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet(
            [
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Description</text:p></table:table-cell>'
                    '<table:table-cell table:number-columns-repeated="2"/>'
                    '<table:table-cell office:value-type="string"><text:p>Price</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Hosting</text:p></table:table-cell>'
                    '<table:table-cell table:number-columns-repeated="2"/>'
                    '<table:table-cell office:value-type="string"><text:p>cheap</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
            ],
            "repeated.ods",
        )

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", row 2, column D (Price) holds "cheap", not a number; enter the price as a number, such as 12.50',
        )

    def test_read_lines_counts_a_merged_cell_as_each_column_it_covers(self):
        """Given a sheet whose line has its description merged across columns A and B, and its price in C,
        when read_lines reads it,
        then the line's price is the one in column C.

        Traces: U-read_lines, P1, sheet reader.
        """
        path = self.sheet(
            [
                ["Description", None, "Price"],
                (
                    "<table:table-row>"
                    '<table:table-cell table:number-columns-spanned="2" office:value-type="string"><text:p>Design</text:p></table:table-cell>'
                    "<table:covered-table-cell/>"
                    '<table:table-cell office:value-type="float" office:value="80"><text:p>80</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
            ],
            "merged.ods",
        )

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("80"), 1)])

    def test_read_lines_leaves_a_cells_comment_out_of_its_text(self):
        """Given a line whose Description cell shows `Design` and holds a comment `ask Ann`,
        when read_lines reads it,
        then the line's description is `Design` alone.

        Traces: U-read_lines, P1, sheet reader.
        """
        path = self.sheet(
            [
                ["Description", "Price"],
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string">'
                    "<office:annotation><text:p>ask Ann</text:p></office:annotation><text:p>Design</text:p>"
                    "</table:table-cell>"
                    '<table:table-cell office:value-type="float" office:value="80"><text:p>80</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
            ],
            "comment.ods",
        )

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("80"), 1)])

    def test_read_lines_skips_empty_rows(self):
        """Given a sheet with an empty row between its two lines,
        when read_lines reads it,
        then it gives the two lines and nothing for the empty row.

        Traces: U-read_lines, P1, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, 1], [], ["Hosting", 5, 2]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("100"), 1), ("Hosting", Decimal("5"), 2)])

    def test_read_lines_counts_an_empty_quantity_as_1(self):
        """Given a line whose Quantity cell is empty,
        when read_lines reads it,
        then its quantity is 1.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, None]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("100"), 1)])

    def test_read_lines_counts_each_quantity_as_1_where_no_column_is_headed_quantity(self):
        """Given a header row of Description and Price alone, and a line,
        when read_lines reads it,
        then the line's quantity is 1.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet([["Description", "Price"], ["Design", 100]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("100"), 1)])

    def test_read_lines_reads_a_currency_price_from_its_stored_value_exactly(self):
        """Given a price cell formatted as currency in EUR, stored as 1234.56 and shown as `1.234,56 €`,
        when read_lines reads it,
        then the price is Decimal 1234.56, the stored value, not the shown text.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", Currency("1234.56", "1.234,56 €"), 1]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("1234.56"), 1)])

    def test_read_lines_rounds_a_currency_price_of_more_than_two_decimals_half_up_to_the_cent(self):
        """Given a price cell formatted as currency in EUR, stored as 1234.565 and shown as `1.234,57 €`,
        when read_lines reads it,
        then the price is Decimal 1234.57, rounded half up to the cent as Calc shows it.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", Currency("1234.565", "1.234,57 €"), 1]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("1234.57"), 1)])

    def test_read_lines_rounds_a_formula_price_to_the_cent(self):
        """Given a price cell holding the formula =100/3, stored as 33.3333333333333,
        when read_lines reads it,
        then the price is Decimal 33.33.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet(
            [
                ["Description", "Price"],
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Design</text:p></table:table-cell>'
                    '<table:table-cell table:formula="of:=100/3" office:value-type="float" office:value="33.3333333333333">'
                    "<text:p>33.3333333333333</text:p></table:table-cell>"
                    "</table:table-row>"
                ),
            ],
            "formula.ods",
        )

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("33.33"), 1)])

    def test_read_lines_keeps_a_price_of_two_decimals_or_fewer_as_stored(self):
        """Given prices 15.5 and 9.99,
        when read_lines reads them,
        then the prices are Decimal 15.5 and 9.99, as stored.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet([HEADER, ["Hosting", Decimal("15.5"), 1], ["Domain", Decimal("9.99"), 1]])

        lines = read_lines(path)

        self.assertEqual(found(lines), [("Hosting", Decimal("15.5"), 1), ("Domain", Decimal("9.99"), 1)])
        self.assertEqual(str(lines[0].price), "15.5", "the price keeps the digits it was stored with")

    def test_read_lines_refuses_a_price_in_another_currency_naming_it(self):
        """Given row 2 whose Price cell is formatted as currency in USD, stored as 12.5 and shown as `$12.50`,
        when read_lines reads it,
        then it refuses, naming row 2, column B (Price), USD, and that invoices are in EUR.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", Currency("12.5", "$12.50", "USD"), 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", row 2, column B (Price) holds "$12.50", a price in USD;'
            " invoices are in EUR, so enter the price in EUR",
        )

    def test_read_lines_reads_a_description_holding_a_link_whole(self):
        """Given a line whose Description cell holds `See ` then a link `the plan` then ` for details`,
        when read_lines reads it,
        then the line's description is `See the plan for details`.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet(
            [
                ["Description", "Price"],
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>See '
                    '<text:a xlink:href="https://example.com/plan" xlink:type="simple">the plan</text:a>'
                    " for details</text:p></table:table-cell>"
                    '<table:table-cell office:value-type="float" office:value="80"><text:p>80</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
            ],
            "link.ods",
        )

        self.assertEqual(found(read_lines(path)), [("See the plan for details", Decimal("80"), 1)])

    def test_read_lines_reads_a_description_holding_a_bold_word_whole(self):
        """Given a line whose Description cell holds `Design ` then a bold `and` then ` build`,
        when read_lines reads it,
        then the line's description is `Design and build`.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet(
            [
                ["Description", "Price"],
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Design '
                    '<text:span text:style-name="T1">and</text:span> build</text:p></table:table-cell>'
                    '<table:table-cell office:value-type="float" office:value="80"><text:p>80</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
            ],
            "bold.ods",
        )

        self.assertEqual(found(read_lines(path)), [("Design and build", Decimal("80"), 1)])

    def test_read_lines_takes_the_first_non_empty_row_as_the_header(self):
        """Given a sheet whose rows 1 and 2 are empty and whose header is row 3,
        when read_lines reads it,
        then it gives the line under the header.

        Traces: U-read_lines, P1, sheet reader.
        """
        path = self.sheet([[], [], HEADER, ["Design", 100, 1]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("100"), 1)])

    def test_read_lines_refuses_a_missing_file(self):
        """Given a path where no file lies,
        when read_lines reads it,
        then it refuses, naming the file and that it can't be read.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.path("missing.ods")

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f"{path}: can't be read (No such file or directory); give the path of the .ods file saved from Calc",
        )

    def test_read_lines_refuses_a_text_file(self):
        """Given a text file named .ods,
        when read_lines reads it,
        then it refuses, naming the file and how to save it as .ods.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.path("invoice.ods")
        with open(path, "w", encoding="utf-8") as file:
            file.write("Design;100;1\n")

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), not_ods(path))

    def test_read_lines_refuses_a_zip_file_that_isnt_opendocument(self):
        """Given a zip file with no mimetype, as an .xlsx file is,
        when read_lines reads it,
        then it refuses, naming the file and how to save it as .ods.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.path("invoice.xlsx")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("xl/workbook.xml", "<workbook/>")

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), not_ods(path))

    def test_read_lines_refuses_an_opendocument_file_that_isnt_a_spreadsheet(self):
        """Given an OpenDocument text file, whose mimetype is that of a text,
        when read_lines reads it,
        then it refuses, naming the file and how to save it as .ods.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = write_tables(self.path("letter.odt"), "", "application/vnd.oasis.opendocument.text")

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), not_ods(path))

    def test_read_lines_refuses_a_header_row_without_description(self):
        """Given a header row of Item, Price, Quantity,
        when read_lines reads it,
        then it refuses, naming the header row and the missing Description.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([["Item", "Price", "Quantity"], ["Design", 100, 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), missing_header(path, 1, "Description"))

    def test_read_lines_refuses_a_header_row_without_price(self):
        """Given empty rows 1 and 2, then a header row of Description, Cost, Quantity,
        when read_lines reads it,
        then it refuses, naming the header row, row 3, and the missing Price.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([[], [], ["Description", "Cost", "Quantity"], ["Design", 100, 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), missing_header(path, 3, "Price"))

    def test_read_lines_refuses_a_header_row_with_two_price_columns(self):
        """Given a header row of Description, Price, Price,
        when read_lines reads it,
        then it refuses, naming both columns, B and C, since either could hold the prices.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([["Description", "Price", "Price"], ["Design", 100, 90]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", the header row, row 1, has two columns headed Price, B and C; keep one',
        )

    def test_read_lines_refuses_a_row_with_no_description(self):
        """Given row 3 with a price and a quantity but an empty Description cell,
        when read_lines reads it,
        then it refuses, naming row 3 and column A (Description).

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, 1], [None, 5, 2]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", row 3, column A (Description) is empty; give each line a description, or empty the whole row',
        )

    def test_read_lines_refuses_a_description_of_spaces_alone(self):
        """Given row 2 whose Description cell holds only spaces,
        when read_lines reads it,
        then it refuses, naming row 2 and column A (Description) as empty.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["   ", 100, 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", row 2, column A (Description) is empty; give each line a description, or empty the whole row',
        )

    def test_read_lines_refuses_a_text_price(self):
        """Given row 3 whose Price cell holds the text `12,50 EUR`,
        when read_lines reads it,
        then it refuses, naming row 3, column B (Price), and the text.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, 1], ["Hosting", "12,50 EUR", 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", row 3, column B (Price) holds "12,50 EUR", not a number; enter the price as a number, such as 12.50',
        )

    def test_read_lines_refuses_a_price_cell_formatted_as_text_saying_how_to_make_it_a_number(self):
        """Given row 2 whose Price cell, formatted as text, holds `12.50`,
        when read_lines reads it,
        then it refuses, naming row 2, column B (Price), that the cell is formatted as text, and how
        to make it a number in Calc.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", "12.50", 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), formatted_as_text(path, 2, "B (Price)", "12.50", "price"))

    def test_read_lines_refuses_a_price_cell_formatted_as_text_holding_a_decimal_comma(self):
        """Given row 2 whose Price cell, formatted as text, holds `12,50`,
        when read_lines reads it,
        then it refuses, naming row 2, column B (Price), that the cell is formatted as text, and how
        to make it a number in Calc.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", "12,50", 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), formatted_as_text(path, 2, "B (Price)", "12,50", "price"))

    def test_read_lines_refuses_a_quantity_cell_formatted_as_text_saying_how_to_make_it_a_number(self):
        """Given row 2 whose Quantity cell, formatted as text, holds `2`,
        when read_lines reads it,
        then it refuses, naming row 2, column C (Quantity), that the cell is formatted as text, and
        how to make it a number in Calc.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, "2"]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), formatted_as_text(path, 2, "C (Quantity)", "2", "quantity"))

    def test_read_lines_refuses_an_empty_price(self):
        """Given row 2 whose Price cell is empty,
        when read_lines reads it,
        then it refuses, naming row 2, column B (Price), and that it holds nothing.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", None, 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", row 2, column B (Price) holds nothing, not a number; enter the price as a number, such as 12.50',
        )

    def test_read_lines_refuses_a_quantity_of_0(self):
        """Given row 2 whose Quantity is 0,
        when read_lines reads it,
        then it refuses, naming row 2, column C (Quantity), and the 0.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, 0]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), wrong_quantity(path, 2, '"0"'))

    def test_read_lines_refuses_a_quantity_of_1_5(self):
        """Given row 2 whose Quantity is 1.5,
        when read_lines reads it,
        then it refuses, naming row 2, column C (Quantity), and the 1.5.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, Decimal("1.5")]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), wrong_quantity(path, 2, '"1.5"'))

    def test_read_lines_refuses_a_text_quantity(self):
        """Given row 2 whose Quantity cell holds the text `two`,
        when read_lines reads it,
        then it refuses, naming row 2, column C (Quantity), and the text.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, "two"]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), wrong_quantity(path, 2, '"two"'))

    def test_read_lines_accepts_a_quantity_of_1(self):
        """Given row 2 whose Quantity is 1, the least that a quantity may be,
        when read_lines reads it,
        then the line's quantity is 1.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, 1]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("100"), 1)])

    def test_read_lines_refuses_a_sheet_of_a_header_alone(self):
        """Given a sheet of a header row and no line,
        when read_lines reads it,
        then it refuses, naming the file and that its first sheet has no lines.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), no_lines(path))

    def test_read_lines_refuses_an_empty_sheet(self):
        """Given a sheet with no row that holds anything,
        when read_lines reads it,
        then it refuses, naming the file and that its first sheet has no lines.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([[], []])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), no_lines(path))

    def test_read_lines_counts_blank_rows_saved_as_one_repeated_row_in_a_refusals_row_number(self):
        """Given a sheet whose header is row 1, a line row 2, then three blank rows that Calc saves
        as one row repeated three times, and row 6 holding text in its Price column,
        when read_lines reads it,
        then the refusal names row 6, as Calc shows it.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet(
            [
                ["Description", "Price"],
                ["Design", 100],
                '<table:table-row table:number-rows-repeated="3"><table:table-cell table:number-columns-repeated="2"/></table:table-row>',
                ["Hosting", "cheap"],
            ],
            "blank.ods",
        )

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", row 6, column B (Price) holds "cheap", not a number; enter the price as a number, such as 12.50',
        )

    def test_read_lines_fills_each_column_of_a_cell_saved_as_repeated(self):
        """Given a line whose Price and Quantity are both 2, which Calc saves as one cell repeated
        over two columns,
        when read_lines reads it,
        then the line's price is 2 and its quantity is 2.

        Traces: U-read_lines, P1, sheet reader.
        """
        path = self.sheet(
            [
                ["Description", "Price", "Quantity"],
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Design</text:p></table:table-cell>'
                    '<table:table-cell table:number-columns-repeated="2" office:value-type="float" office:value="2">'
                    "<text:p>2</text:p></table:table-cell>"
                    "</table:table-row>"
                ),
            ],
            "repeated.ods",
        )

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("2"), 2)])

    def test_read_lines_finds_a_header_with_spaces_around_it(self):
        """Given a header row of ` Description`, `Price `, and `  Quantity  `, and a line,
        when read_lines reads it,
        then it finds each column and gives the line.

        Traces: U-read_lines, P1, sheet reader.
        """
        path = self.sheet([[" Description", "Price ", "  Quantity  "], ["Design", 100, 2]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("100"), 2)])

    def test_read_lines_trims_spaces_around_a_description(self):
        """Given a line whose Description cell holds `  Design  `,
        when read_lines reads it,
        then the line's description is `Design`.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet([HEADER, ["  Design  ", 100, 1]])

        self.assertEqual(found(read_lines(path)), [("Design", Decimal("100"), 1)])

    def test_read_lines_names_the_first_tab_in_a_refusal_when_the_lines_sit_on_a_later_tab(self):
        """Given a file whose first tab, `Clients`, has the header Name, Address, and whose second
        tab, `Invoice`, holds the lines,
        when read_lines reads it,
        then the refusal names the first sheet `Clients`, so the user sees which tab was read.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        first = table([["Name", "Address"], ["Acme", "Main Street 1"]], "Clients")
        second = table([HEADER, ["Design", 100, 1]], "Invoice")
        path = write_tables(self.path("tabs.ods"), first + second)

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Clients", the header row, row 1, has no column headed Description;'
            " the header row needs Description and Price, and may have Quantity",
        )

    def test_read_lines_refuses_a_spreadsheet_whose_content_isnt_xml(self):
        """Given a zip with the .ods mimetype whose content.xml is cut off mid-tag,
        when read_lines reads it,
        then it refuses, naming the file and to save it again from Calc as .ods.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.path("damaged.ods")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(zipfile.ZipInfo("mimetype"), MIMETYPE)
            archive.writestr("content.xml", "<office:document-content><office:bo")

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), damaged(path))

    def test_read_lines_refuses_a_spreadsheet_with_no_content(self):
        """Given a zip with the .ods mimetype and no content.xml,
        when read_lines reads it,
        then it refuses, naming the file and to save it again from Calc as .ods.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.path("damaged.ods")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(zipfile.ZipInfo("mimetype"), MIMETYPE)

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), damaged(path))

    def test_read_lines_refuses_a_spreadsheet_that_holds_no_sheet(self):
        """Given an .ods file whose content holds no sheet,
        when read_lines reads it,
        then it refuses, naming the file and to save it again from Calc as .ods.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = write_tables(self.path("empty.ods"), "")

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), damaged(path))

    def test_read_lines_refuses_a_spreadsheet_whose_stored_content_is_corrupted(self):
        """Given an .ods file whose content.xml, stored uncompressed, has bytes overwritten, so its
        checksum no longer matches,
        when read_lines reads it,
        then it refuses, naming the file and to save it again from Calc as .ods.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.path("damaged.ods")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(zipfile.ZipInfo("mimetype"), MIMETYPE)
            archive.writestr("content.xml", "<office:document-content>" + "x" * 100, zipfile.ZIP_STORED)
        overwrite_content(path)

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), damaged(path))

    def test_read_lines_refuses_a_spreadsheet_whose_compressed_content_is_corrupted(self):
        """Given an .ods file whose content.xml, compressed, has bytes overwritten, so it no longer
        decompresses,
        when read_lines reads it,
        then it refuses, naming the file and to save it again from Calc as .ods.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.path("damaged.ods")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(zipfile.ZipInfo("mimetype"), MIMETYPE)
            archive.writestr("content.xml", "<office:document-content>" + "hello world " * 50, zipfile.ZIP_DEFLATED)
        overwrite_content(path)

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), damaged(path))

    def test_read_lines_joins_a_description_of_two_lines_with_a_space(self):
        """Given a line whose Description cell was typed on two lines, `Design` and `and build`,
        which Calc saves as two paragraphs of the cell,
        when read_lines reads it,
        then the line's description is `Design and build`, one invoice row.

        Traces: U-read_lines, S1, sheet reader.
        """
        path = self.sheet(
            [
                ["Description", "Price"],
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Design</text:p><text:p>and build</text:p>'
                    "</table:table-cell>"
                    '<table:table-cell office:value-type="float" office:value="80"><text:p>80</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
            ],
            "two-lines.ods",
        )

        self.assertEqual(found(read_lines(path)), [("Design and build", Decimal("80"), 1)])

    def test_read_lines_refuses_a_price_cell_formatted_as_text_holding_a_negative_number(self):
        """Given row 2 whose Price cell, formatted as text, holds `-12.50`,
        when read_lines reads it,
        then it refuses, naming row 2, column B (Price), that the cell is formatted as text, and how
        to make it a number in Calc.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Refund", "-12.50", 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), formatted_as_text(path, 2, "B (Price)", "-12.50", "price"))

    def test_read_lines_refuses_a_price_cell_formatted_as_text_holding_a_number_with_spaces_around_it(self):
        """Given row 2 whose Price cell, formatted as text, holds ` 12.50 `,
        when read_lines reads it,
        then it refuses, naming row 2, column B (Price), that the cell is formatted as text, and how
        to make it a number in Calc.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", " 12.50 ", 1]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), formatted_as_text(path, 2, "B (Price)", " 12.50 ", "price"))

    def test_read_lines_refuses_a_quantity_cell_formatted_as_currency(self):
        """Given row 2 whose Quantity cell is formatted as currency, showing `€2.00`,
        when read_lines reads it,
        then it refuses, naming row 2, column C (Quantity), as not a whole number of 1 or more.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet([HEADER, ["Design", 100, Currency("2", "€2.00")]])

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), wrong_quantity(path, 2, '"€2.00"'))

    def test_read_lines_refuses_a_quantity_cell_formatted_as_percent(self):
        """Given row 2 whose Quantity cell is formatted as percent, showing `200%`,
        when read_lines reads it,
        then it refuses, naming row 2, column C (Quantity), as not a whole number of 1 or more.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet(
            [
                HEADER,
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Design</text:p></table:table-cell>'
                    '<table:table-cell office:value-type="float" office:value="100"><text:p>100</text:p></table:table-cell>'
                    '<table:table-cell office:value-type="percentage" office:value="2"><text:p>200%</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
            ],
            "percent.ods",
        )

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(str(refused.exception), wrong_quantity(path, 2, '"200%"'))

    def test_read_lines_refuses_a_price_cell_formatted_as_percent(self):
        """Given row 2 whose Price cell is formatted as percent, showing `19%`,
        when read_lines reads it,
        then it refuses, naming row 2, column B (Price), as not a number.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet(
            [
                HEADER,
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Design</text:p></table:table-cell>'
                    '<table:table-cell office:value-type="percentage" office:value="0.19"><text:p>19%</text:p></table:table-cell>'
                    '<table:table-cell office:value-type="float" office:value="1"><text:p>1</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
            ],
            "percent.ods",
        )

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", row 2, column B (Price) holds "19%", not a number; enter the price as a number, such as 12.50',
        )

    def test_read_lines_names_a_column_past_z_by_its_two_letters(self):
        """Given a sheet whose Price column is column number 27, past 25 empty columns written as one
        repeated cell, and whose row 2 holds text there,
        when read_lines reads it,
        then the refusal names row 2 and column AA, as Calc shows it.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.sheet(
            [
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Description</text:p></table:table-cell>'
                    '<table:table-cell table:number-columns-repeated="25"/>'
                    '<table:table-cell office:value-type="string"><text:p>Price</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
                (
                    "<table:table-row>"
                    '<table:table-cell office:value-type="string"><text:p>Hosting</text:p></table:table-cell>'
                    '<table:table-cell table:number-columns-repeated="25"/>'
                    '<table:table-cell office:value-type="string"><text:p>cheap</text:p></table:table-cell>'
                    "</table:table-row>"
                ),
            ],
            "wide.ods",
        )

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f'{path}: first sheet "Sheet1", row 2, column AA (Price) holds "cheap", not a number; enter the price as a number, such as 12.50',
        )

    def test_read_lines_refuses_a_path_that_exists_but_cant_be_opened_with_its_reason(self):
        """Given the path of a folder, which exists but can't be opened as a file,
        when read_lines reads it,
        then it refuses, naming the path and the reason the system gives.

        Traces: U-read_lines, S2, P2, sheet reader.
        """
        path = self.folder

        with self.assertRaises(SheetError) as refused:
            read_lines(path)
        self.assertEqual(
            str(refused.exception),
            f"{path}: can't be read (Is a directory); give the path of the .ods file saved from Calc",
        )


def not_ods(path):
    return (
        f"{path}: isn't a spreadsheet saved as .ods;"
        " in Calc, use File > Save As and choose ODF Spreadsheet (.ods)"
    )


def damaged(path):
    return f"{path}: can't be read as a Calc spreadsheet; save it again from Calc as .ods"


def overwrite_content(path):
    """Overwrites ten bytes of the stored data of content.xml in the zip at path, as a damaged disk might."""
    with open(path, "r+b") as file:
        data = file.read()
        file.seek(data.index(b"content.xml") + len("content.xml") + 5)
        file.write(b"\xff" * 10)


def missing_header(path, row, name):
    return (
        f'{path}: first sheet "Sheet1", the header row, row {row}, has no column headed {name};'
        " the header row needs Description and Price, and may have Quantity"
    )


def wrong_quantity(path, row, held):
    return (
        f'{path}: first sheet "Sheet1", row {row}, column C (Quantity) holds {held}, not a whole number of 1 or more;'
        " enter how many, such as 2, or leave it empty for 1"
    )


def formatted_as_text(path, row, column, held, what):
    return (
        f'{path}: first sheet "Sheet1", row {row}, column {column} holds "{held}" as text, as the cell is formatted as text;'
        f" in Calc, select the cell, choose Format > Cells, pick Number under Category on the Numbers tab,"
        f" and type the {what} again"
    )


def no_lines(path):
    return (
        f'{path}: first sheet "Sheet1" has no lines;'
        " give it a header row of Description, Price, and Quantity, and a row below it for each line"
    )
