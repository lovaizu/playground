"""How an .ods file, as Calc saves it, holds the colleague's invoice: its details and its lines,
read from the first sheet, and each cell refused that would make a wrong invoice."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Union
from xml.etree import ElementTree

from invoicer.lines import Line

_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
_ODS = b"application/vnd.oasis.opendocument.spreadsheet"
# The kinds of cell whose office:value Calc stores as a number, whatever format shows it.
_NUMBER_KINDS = ("float", "currency", "percentage")
# A price typed as text: at most two digits after its one decimal comma or point.
_PRICE = re.compile(r"-?\d+(?:[.,]\d{1,2})?")
# Text of digits with points or commas that isn't such a price, such as `1.200` or `1.200,00`.
_DIGITS_AND_MARKS = re.compile(r"-?[\d.,]*\d[\d.,]*")
# A quantity typed as text: digits with at most one decimal comma or point, such as `2,5`.
# rate.py's _PERCENT reads a typed rate by a pattern alike but apart, as the two rules differ:
# the sheet refuses a quantity such as `1.000` below, and a rate such as `19.000` is 19%.
_QUANTITY = re.compile(r"-?\d+(?:[.,]\d+)?")
# A quantity typed as text that reads two ways, such as `1.000`: a thousand, or 1.
_QUANTITY_TWO_WAYS = re.compile(r"-?\d+[.,]\d{3}")

# Each detail's label in column A, with the field of Details it fills.
_LABELS = [
    ("Invoice number", "invoice_number"),
    ("Date", "date"),
    ("Client name", "client_name"),
    ("Client address", "client_address"),
    ("Our name", "our_name"),
    ("Our address", "our_address"),
    ("Our VAT ID", "our_vat_id"),
]
# The header's names, each naming the column that a Line's field comes from.
_DESCRIPTION = "Description"
_PRICE_HEADER = "Price"
_QUANTITY_HEADER = "Quantity"
_HEADERS = [_DESCRIPTION, _PRICE_HEADER, _QUANTITY_HEADER]
# The header's names as the refusals list them: `Description, Price, and Quantity`.
_HEADERS_LISTED = f"{', '.join(_HEADERS[:-1])}, and {_HEADERS[-1]}"


class SheetError(Exception):
    """A sheet that gives no invoice; its message names the file, the row, or the label, and what
    to fix, such as `row 11: the price is empty`."""


@dataclass
class Details:
    """Who bills whom, under which number and date, each as the sheet's text: a date cell as its
    ISO date, such as `2026-11-19`, and a date typed as text as typed."""

    invoice_number: str
    date: str
    client_name: str
    client_address: str
    our_name: str
    our_address: str
    our_vat_id: str


@dataclass
class _Cell:
    kind: str
    value: str
    text: str


# A row of the sheet as the readers below take it: its number as Calc shows it, and its cells by
# column number counted from 0.
_Row = tuple[int, dict[int, _Cell]]


def read_sheet(path: str) -> tuple[Details, list[Line]]:
    """Gives the details and the lines of the first sheet of the .ods file at path.

    Details: each from the row before the header row whose column A holds its label and whose
    column B its value, empty rows allowed between them. Lines: from the rows right under the header
    row, the first row that names `Description`, `Price`, or `Quantity`, in any column order and
    with empty columns between; they end at the first empty row. Rows count as Calc numbers them,
    a row that Calc saves once as repeated counting as each of its copies.

    A price or quantity comes from a number cell, Currency and Percent cells among them, by the
    value Calc stores for it, even where the cell shows no text, or from a text cell holding a
    number with a decimal comma or point, such as `80,00`. A price is the exact Decimal of that
    value, never rounded here, and may be 0 or below, as for a discount; as text it takes at most
    two digits after its decimal mark. A quantity is an int where it's whole and an exact Decimal
    where not, such as 2.5 hours, and must be more than 0.

    Labels and header names are found with any spaces around them, as if typed without them.

    Refuses: SheetError, whose message names what to fix, for: a missing file; a folder, with
    `<path> is a folder; give the .ods file inside it`; a file the laptop won't let invoicer read,
    with `<path> can't be opened: you may not read it. Ask whoever shared it to give you access.`;
    a file that isn't an .ods spreadsheet; a missing label; a label given twice, naming both rows;
    a label whose value is empty, such as `row 3: the Client name is empty`; no header row; a
    header that lacks a name or names one twice, naming its columns as Calc shows them, such as
    B or AA; an empty description; a price or quantity that's empty, such as `row 11: the price
    is empty`, or not a number; a price typed as text such as `1.200` or `1,200`, with `row N:
    write the price as a plain number, such as 1200.00`; a quantity typed as text with three digits
    after its one comma or point, such as `1.000`, with `row N: write the quantity as a plain
    number, such as 1000`; a quantity of 0 or below; no lines; and a row that holds anything below
    the empty row where the lines end, naming both rows."""
    rows = _rows(_first_sheet(path))
    header_number, header_cells = _header_row(rows)
    details = _details([(number, cells) for number, cells in rows if number < header_number])
    lines = _lines(rows, header_number, _columns(header_number, header_cells))
    return details, lines


def _first_sheet(path: str) -> ElementTree.Element:
    """The first sheet of the .ods file at path, which its content.xml holds as its first
    table:table element."""
    try:
        with zipfile.ZipFile(path) as ods:
            names = ods.namelist()
            if "content.xml" not in names or "mimetype" not in names or ods.read("mimetype") != _ODS:
                raise SheetError(_not_ods(path))
            content = ods.read("content.xml")
    except FileNotFoundError:
        raise SheetError(f"{path}: there's no such file: check the sheet's name and folder") from None
    except IsADirectoryError:
        raise SheetError(f"{path} is a folder; give the .ods file inside it") from None
    except PermissionError:
        raise SheetError(
            f"{path} can't be opened: you may not read it. Ask whoever shared it to give you access."
        ) from None
    except zipfile.BadZipFile:
        raise SheetError(_not_ods(path)) from None
    try:
        sheet = ElementTree.fromstring(content).find(f".//{{{_TABLE}}}table")
    except ElementTree.ParseError:
        raise SheetError(_not_ods(path)) from None
    if sheet is None:
        raise SheetError(_not_ods(path))
    return sheet


def _not_ods(path: str) -> str:
    return f"{path} isn't an .ods spreadsheet: save the sheet in Calc as ODF Spreadsheet (.ods)"


def _rows(sheet: ElementTree.Element) -> list[_Row]:
    """Each row of the sheet that holds a cell, numbered from 1 as Calc shows it, a repeated row
    giving each of its copies."""
    rows = []
    number = 1
    for row_element in sheet.iter(f"{{{_TABLE}}}table-row"):
        times = int(row_element.get(f"{{{_TABLE}}}number-rows-repeated", "1"))
        cells = _cells(row_element)
        if cells:
            rows.extend((number + copy, cells) for copy in range(times))
        number += times
    return rows


def _cells(row_element: ElementTree.Element) -> dict[int, _Cell]:
    """The cells of the row element that hold a value or text, by column number counted from 0."""
    cells = {}
    column = 0
    for cell_element in row_element:
        times = int(cell_element.get(f"{{{_TABLE}}}number-columns-repeated", "1"))
        cell = _read_cell(cell_element)
        if cell is not None:
            for copy in range(times):
                cells[column + copy] = cell
        column += times
    return cells


def _read_cell(cell_element: ElementTree.Element) -> Optional[_Cell]:
    """The cell element's kind, value, and text, or None where it holds neither value nor text."""
    kind = cell_element.get(f"{{{_OFFICE}}}value-type", "")
    if kind == "date":
        # Calc saves a date with a time as `2026-11-19T10:30:00`; the invoice takes its date alone.
        value = cell_element.get(f"{{{_OFFICE}}}date-value", "")[:10]
    else:
        value = cell_element.get(f"{{{_OFFICE}}}value", "")
    paragraphs = cell_element.findall(f"{{{_TEXT}}}p")
    text = "\n".join("".join(paragraph.itertext()) for paragraph in paragraphs)
    if not kind and not text:
        return None
    return _Cell(kind, value, text)


def _header_row(rows: list[_Row]) -> _Row:
    """The first row that names any of the header's names, with its number."""
    for number, cells in rows:
        if any(cell.text.strip() in _HEADERS for cell in cells.values()):
            return number, cells
    raise SheetError(
        f"the sheet has no header row: put a row naming {_HEADERS_LISTED} below the details"
    )


def _detail_text(cell: Optional[_Cell]) -> str:
    """A detail's text: a date cell's ISO date, and any other cell's text as Calc shows it."""
    if cell is None:
        return ""
    if cell.kind == "date":
        return cell.value
    return cell.text.strip()


def _details(rows: list[_Row]) -> Details:
    """The Details from the rows before the header row, each found by its label in column A."""
    known = {label for label, _ in _LABELS}
    by_label = {}
    for number, cells in rows:
        label_cell = cells.get(0)
        label = "" if label_cell is None else label_cell.text.strip()
        if label not in known:
            continue
        if label in by_label:
            raise SheetError(
                f"rows {by_label[label][0]} and {number} both hold the label `{label}`: keep the "
                "row with this invoice's value and delete the other"
            )
        by_label[label] = (number, cells.get(1))
    values = {}
    for label, field in _LABELS:
        if label not in by_label:
            raise SheetError(
                f"the `{label}` row is missing: put `{label}` in column A of a row above the "
                "header and its value in column B"
            )
        number, value_cell = by_label[label]
        values[field] = _detail_text(value_cell)
        if not values[field]:
            raise SheetError(f"row {number}: the {label} is empty")
    return Details(**values)


def _columns(header_number: int, header_cells: dict[int, _Cell]) -> dict[str, int]:
    """The column of each of the header's names in the header row."""
    columns = {}
    for column, cell in sorted(header_cells.items()):
        name = cell.text.strip()
        if name not in _HEADERS:
            continue
        if name in columns:
            raise SheetError(
                f"row {header_number}: the header names {name} twice, in columns "
                f"{_letter(columns[name])} and {_letter(column)}: rename or clear one of them"
            )
        columns[name] = column
    for name in _HEADERS:
        if name not in columns:
            raise SheetError(
                f"row {header_number}: the header has no {name} column: name its column {name}, "
                f"as {_HEADERS_LISTED}"
            )
    return columns


def _letter(column: int) -> str:
    """The column's letters as Calc shows them, such as 0 -> A and 26 -> AA."""
    letters = ""
    column += 1
    while column:
        column, rest = divmod(column - 1, 26)
        letters = chr(ord("A") + rest) + letters
    return letters


def _lines(rows: list[_Row], header_number: int, columns: dict[str, int]) -> list[Line]:
    """The Line of each row right under the header row, up to the first empty row, refusing a
    row that holds anything below it and a sheet with no lines."""
    lines = []
    # The number the next row of lines has; a row past it lies below an empty row.
    next_number = header_number + 1
    for number, cells in rows:
        if number < next_number:
            continue
        if number > next_number:
            raise SheetError(
                f"row {number} holds text below the empty row {next_number}, where the lines end: "
                f"delete the empty row {next_number} to bill row {number}, or clear row {number}"
            )
        lines.append(_line(number, cells, columns))
        next_number += 1
    if not lines:
        raise SheetError(
            "the sheet has no lines: put each line in the rows right under the header in row "
            f"{header_number}"
        )
    return lines


def _line(row_number: int, cells: dict[int, _Cell], columns: dict[str, int]) -> Line:
    """The Line of the row numbered row_number, its description stripped of spaces around it."""
    description_cell = cells.get(columns[_DESCRIPTION])
    description = "" if description_cell is None else description_cell.text.strip()
    if not description:
        raise SheetError(f"row {row_number}: the description is empty")
    price = _price(row_number, cells.get(columns[_PRICE_HEADER]))
    quantity = _quantity(row_number, cells.get(columns[_QUANTITY_HEADER]))
    return Line(description, price, quantity)


def _price(row_number: int, cell: Optional[_Cell]) -> Decimal:
    """The exact Decimal of the price cell of the row numbered row_number."""
    text = _filled(row_number, cell, "price")
    if cell.kind in _NUMBER_KINDS:
        return Decimal(cell.value)
    if _PRICE.fullmatch(text):
        return Decimal(text.replace(",", "."))
    if _DIGITS_AND_MARKS.fullmatch(text):
        raise SheetError(f"row {row_number}: write the price as a plain number, such as 1200.00")
    raise SheetError(
        f"row {row_number}: the price `{text}` isn't a number: type it as a number, such as 80.00"
    )


def _quantity(row_number: int, cell: Optional[_Cell]) -> Union[int, Decimal]:
    """The quantity of the row numbered row_number: an int where it's whole, and an exact Decimal
    where not."""
    text = _filled(row_number, cell, "quantity")
    if cell.kind in _NUMBER_KINDS:
        quantity = Decimal(cell.value)
    elif _QUANTITY_TWO_WAYS.fullmatch(text):
        raise SheetError(f"row {row_number}: write the quantity as a plain number, such as 1000")
    elif _QUANTITY.fullmatch(text):
        quantity = Decimal(text.replace(",", "."))
    else:
        raise SheetError(
            f"row {row_number}: the quantity `{text}` isn't a number: type how many as a number, "
            "such as 10"
        )
    if quantity <= 0:
        raise SheetError(
            f"row {row_number}: the quantity is {quantity}: type how many, more than 0"
        )
    if quantity == quantity.to_integral_value():
        return int(quantity)
    return quantity


def _filled(row_number: int, cell: Optional[_Cell], what: str) -> str:
    """The cell's text, refusing a cell that holds neither value nor text."""
    if cell is None or (not cell.value and not cell.text.strip()):
        raise SheetError(f"row {row_number}: the {what} is empty")
    return cell.text.strip()
