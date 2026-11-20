"""The spreadsheet that the accounting team keeps, and how its cells become an invoice's lines: the
.ods file as Calc saves it, its first sheet, the header row naming the columns, and each row below
it as one line."""

from __future__ import annotations

import re
import zipfile
import zlib
from decimal import Decimal
from xml.etree import ElementTree

from invoicer.lines import Line
from invoicer.render import INVOICE_CURRENCY
from invoicer.tax import round_to_cent

_MIMETYPE = b"application/vnd.oasis.opendocument.spreadsheet"
_OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
# Each column that the reader takes, by its header in lower case, which finds it in any letter case,
# with its header as a refusal names it.
_HEADERS = {"description": "Description", "price": "Price", "quantity": "Quantity"}
# The value types of a cell that holds a price.
_PRICE_KINDS = ("float", "currency")
# Text that Calc would read as a number, had its cell not been formatted as text.
_NUMBER_AS_TEXT = re.compile(r"[+-]?\d+(?:[.,]\d+)?")


class SheetError(Exception):
    """A fault of the spreadsheet that keeps it from giving an invoice's lines. Its message is one
    line that names the file, the first sheet by its tab's name where the sheet is at fault, the
    row and column as Calc shows them where a cell is at fault, and what to fix."""


class _Cell:
    """A cell that holds something: its value type, its stored value, its currency, and the text
    Calc shows."""

    def __init__(self, kind: str | None, value: str | None, currency: str | None, shown: str):
        self.kind = kind
        self.value = value
        self.currency = currency
        self.shown = shown


def read_lines(path: str) -> list[Line]:
    """Gives the lines of the .ods file at path, in sheet order: one for each non-empty row below
    the header, the first non-empty row of the first sheet. The header names the columns
    Description, Price, and Quantity, in any order and letter case, and other columns are left
    out. Each line's description is the whole text its cell shows, links and bold words included,
    without the spaces around it. Its price is the Decimal stored in its cell, not the text the
    cell shows, rounded half up to the cent where it has more than two decimals, such as the
    33.3333333333333 of the formula =100/3, and kept as stored otherwise. Its quantity is an int,
    1 where the cell is empty or no column is headed Quantity.

    Raises SheetError, naming the file, where it is missing or can't be read, isn't an .ods
    spreadsheet, or is an .ods file too damaged to read or holding no sheet; naming the first
    sheet by its tab's name too where it has no line, or a header row lacking Description or Price
    or heading two columns alike; and naming the row and column too where a row has no
    description, a price or quantity cell formatted as text holds a number, a price isn't a number
    or is in a currency other than the invoice's, or a quantity isn't a whole number of 1 or more."""
    sheet = _first_sheet(path)
    tab = sheet.get(f"{_TABLE}name")
    place = f'{path}: first sheet "{tab}"'
    rows = _rows(sheet)
    header = next(rows, None)
    lines = []
    if header is not None:
        columns = _columns(place, *header)
        lines = [_line(place, number, cells, columns) for number, cells in rows]
    if not lines:
        raise SheetError(
            f"{place} has no lines; give it a header row of {_HEADERS['description']}, {_HEADERS['price']},"
            f" and {_HEADERS['quantity']}, and a row below it for each line"
        )
    return lines


def _first_sheet(path: str) -> ElementTree.Element:
    """The first sheet of the .ods file."""
    content = _content(path)
    sheet = None
    if content is not None:
        try:
            sheet = ElementTree.fromstring(content).find(f".//{_TABLE}table")
        except ElementTree.ParseError:
            pass
    if sheet is None:
        raise SheetError(f"{path}: can't be read as a Calc spreadsheet; save it again from Calc as .ods")
    return sheet


def _content(path: str) -> bytes | None:
    """The content.xml of the .ods file, which holds its sheets, or None where it's missing or damaged."""
    try:
        with zipfile.ZipFile(path) as archive:
            mimetype = _member(archive, "mimetype")
            content = _member(archive, "content.xml")
    except OSError as error:
        raise SheetError(
            f"{path}: can't be read ({error.strerror}); give the path of the .ods file saved from Calc"
        ) from None  # The refusal names the system's reason itself, so the OSError adds nothing to it.
    except zipfile.BadZipFile:
        mimetype = None
    if mimetype != _MIMETYPE:
        raise SheetError(
            f"{path}: isn't a spreadsheet saved as .ods;"
            " in Calc, use File > Save As and choose ODF Spreadsheet (.ods)"
        )
    return content


def _member(archive: zipfile.ZipFile, name: str) -> bytes | None:
    """The bytes of the archive's member of that name, or None where it's missing or damaged."""
    try:
        return archive.read(name)
    except (KeyError, zipfile.BadZipFile, zlib.error):
        return None


def _rows(sheet: ElementTree.Element):
    """Each row of the sheet that holds something, as its row number as Calc shows it and its
    cells by column number from 0."""
    number = 0
    for row in sheet.iter(f"{_TABLE}table-row"):
        repeated = int(row.get(f"{_TABLE}number-rows-repeated", "1"))
        cells = _cells(row)
        if not cells:
            number += repeated
            continue
        for _ in range(repeated):
            number += 1
            yield number, cells


def _cells(row: ElementTree.Element) -> dict[int, _Cell]:
    """The cells of the row that hold something, by column number from 0; a merged cell's covered
    cells count as the columns they cover, and a cell's comment is no part of its text."""
    found = {}
    column = 0
    for cell in row:
        repeated = int(cell.get(f"{_TABLE}number-columns-repeated", "1"))
        kind = cell.get(f"{_OFFICE}value-type")
        # Calc saves each line of a cell typed on several lines as a paragraph of its own; a space
        # joins them, so such a description prints as one invoice row.
        shown = " ".join("".join(p.itertext()) for p in cell.findall(f"{_TEXT}p"))
        if kind is not None or shown:
            parsed = _Cell(kind, cell.get(f"{_OFFICE}value"), cell.get(f"{_OFFICE}currency"), shown)
            for offset in range(repeated):
                found[column + offset] = parsed
        column += repeated
    return found


def _columns(place: str, number: int, cells: dict[int, _Cell]) -> dict[str, int]:
    """The column of each header the header row names, by its key in _HEADERS; place names the
    file and the sheet in a refusal."""
    found = {}
    for column in sorted(cells):
        name = cells[column].shown.strip().casefold()
        if name in found:
            raise SheetError(
                f"{place}, the header row, row {number}, has two columns headed {_HEADERS[name]},"
                f" {_letter(found[name])} and {_letter(column)}; keep one"
            )
        if name in _HEADERS:
            found[name] = column
    for name in ("description", "price"):
        if name not in found:
            raise SheetError(
                f"{place}, the header row, row {number}, has no column headed {_HEADERS[name]};"
                f" the header row needs {_HEADERS['description']} and {_HEADERS['price']},"
                f" and may have {_HEADERS['quantity']}"
            )
    return found


def _line(place: str, number: int, cells: dict[int, _Cell], columns: dict[str, int]) -> Line:
    """The line of one row, or SheetError naming the row and the column at fault after place, which
    names the file and the sheet."""

    def where(name):
        return f"{place}, row {number}, column {_letter(columns[name])} ({_HEADERS[name]})"

    description = _description(cells.get(columns["description"]), where("description"))
    price = _price(cells.get(columns["price"]), where("price"))
    quantity_cell = cells.get(columns["quantity"]) if "quantity" in columns else None
    quantity = 1 if quantity_cell is None else _quantity(quantity_cell, where("quantity"))
    return Line(description, price, quantity)


def _description(cell: _Cell | None, where: str) -> str:
    """The text that a Description cell shows, without the spaces around it; where names the cell
    in a refusal."""
    if cell is None or not cell.shown.strip():
        raise SheetError(f"{where} is empty; give each line a description, or empty the whole row")
    return cell.shown.strip()


def _price(cell: _Cell | None, where: str) -> Decimal:
    """The Decimal that a Price cell stores, rounded half up to the cent where it has more than two
    decimals; where names the cell in a refusal."""
    _refuse_number_as_text(cell, where, "price")
    if cell is None or cell.kind not in _PRICE_KINDS:
        raise SheetError(f"{where} holds {_held(cell)}, not a number; enter the price as a number, such as 12.50")
    if cell.kind == "currency" and cell.currency != INVOICE_CURRENCY:
        raise SheetError(
            f"{where} holds {_held(cell)}, a price in {cell.currency};"
            f" invoices are in {INVOICE_CURRENCY}, so enter the price in {INVOICE_CURRENCY}"
        )
    stored = Decimal(cell.value)
    rounded = round_to_cent(stored)
    # Only a price past the cent is rounded, so a price such as 15.5 or 1200 keeps the digits that
    # the invoice shows for it, in place of 15.50 or 1200.00.
    return stored if rounded == stored else rounded


def _quantity(cell: _Cell, where: str) -> int:
    """The whole number of 1 or more that a Quantity cell holds; where names the cell in a refusal."""
    _refuse_number_as_text(cell, where, "quantity")
    count = Decimal(cell.value) if cell.kind == "float" else None
    if count is None or count < 1 or count != count.to_integral_value():
        raise SheetError(
            f"{where} holds {_held(cell)}, not a whole number of 1 or more;"
            " enter how many, such as 2, or leave it empty for 1"
        )
    return int(count)


def _refuse_number_as_text(cell: _Cell | None, where: str, name: str) -> None:
    """Raises SheetError where the cell, formatted as text, holds what Calc would read as a number,
    saying how to make it a number; where names the cell, and name what it holds, price or quantity."""
    if cell is not None and cell.kind == "string" and _NUMBER_AS_TEXT.fullmatch(cell.shown.strip()):
        raise SheetError(
            f"{where} holds {_held(cell)} as text, as the cell is formatted as text;"
            " in Calc, select the cell, choose Format > Cells, pick Number under Category on the Numbers tab,"
            f" and type the {name} again"
        )


def _held(cell: _Cell | None) -> str:
    """What a cell at fault holds, as a refusal names it."""
    return "nothing" if cell is None else '"' + cell.shown + '"'


def _letter(column: int) -> str:
    """The column's letters as Calc shows them, A for column 0."""
    # Calc's letters count A to Z, then AA, with no letter for zero, so each turn counts from 1 and
    # takes 1 away before divmod: column 25 is Z, and column 26 is AA.
    letters = ""
    column += 1
    while column:
        column, rest = divmod(column - 1, 26)
        letters = chr(ord("A") + rest) + letters
    return letters
