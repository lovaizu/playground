"""The lines that a Calc .ods file keeps on its first sheet under Description, Price, Quantity."""

from __future__ import annotations

import os
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from xml.etree import ElementTree

from invoicer.lines import Line
from invoicer.refusal import Refusal

_MIMETYPE = b"application/vnd.oasis.opendocument.spreadsheet"
_OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
_COLUMNS = ("Description", "Price", "Quantity")
_CENT = Decimal("0.01")
_PRICE = "Type it as a number to the cent, such as 14.50."
_QUANTITY = "Type a whole number from 1, such as 9."


@dataclass(frozen=True)
class _Cell:
    """A cell that holds something: its office:value-type, its office:value or None, and its text."""

    kind: str
    value: str | None
    text: str

    def number(self) -> Decimal | None:
        """The cell's number, or None where Calc keeps it as text or as a kind that isn't a number."""
        if self.kind in ("float", "currency") and self.value is not None:
            return Decimal(self.value)
        return None


_Row = dict[int, _Cell]


def read(path: str) -> list[Line]:
    """The lines of the .ods file at `path`, in the order of its rows.

    Takes: the path of the file, from the folder the command runs in.
    Gives: one library Line for each row under row 1, its price a Decimal to the cent and its
    quantity a whole number from 1; a row whose three cells are empty gives none.
    Changes: nothing; it only reads the file, with Python's standard library alone.
    Refuses: Refusal naming the first wrong place it meets, each row by its number as Calc shows
    it: the file where it's missing or isn't an .ods file; the column where row 1 lacks
    Description, Price, or Quantity; the row whose price isn't a number to the cent, whose
    quantity isn't a whole number from 1, or that has a price and a quantity but no
    description; and the file where its first sheet holds no line.
    """
    rows = _rows(_first_sheet(path))
    number, heading = next(rows, (1, {}))
    found: dict[str, int] = {}
    for column, cell in sorted(heading.items()):
        found.setdefault(cell.text.strip(), column)
    for name in _COLUMNS:
        if number != 1 or name not in found:
            raise Refusal(
                f"{path}, row 1: no column is named {name}. Name the columns of the lines"
                " Description, Price, and Quantity in row 1."
            )
    columns = [found[name] for name in _COLUMNS]
    lines = [
        _line(f"{path}, row {number}", *[cells.get(column) for column in columns])
        for number, cells in rows
        if any(column in cells for column in columns)
    ]
    if not lines:
        raise Refusal(
            f"{path}: its first sheet holds no line under row 1. Type each line of the invoice"
            " under Description, Price, and Quantity."
        )
    return lines


def _first_sheet(path: str) -> ElementTree.Element:
    """The table:table of the file's first sheet, once the file proves an .ods file."""
    if not os.path.isfile(path):
        raise Refusal(
            f"{path}: no such file is here. Give the path of the .ods file that keeps the"
            " invoice's lines, such as October.ods in the folder you run invoicer in."
        )
    wrong = Refusal(
        f"{path} isn't an .ods file. Save it in Calc as ODF Spreadsheet (.ods), and give"
        " that file."
    )
    if not zipfile.is_zipfile(path):
        raise wrong
    with zipfile.ZipFile(path) as archive:
        if (
            "mimetype" not in archive.namelist()
            or archive.read("mimetype") != _MIMETYPE
        ):
            raise wrong
        content = ElementTree.fromstring(archive.read("content.xml"))
    return next(content.iter(f"{_TABLE}table"))


def _rows(sheet: ElementTree.Element) -> Iterator[tuple[int, _Row]]:
    """Each row of the sheet that holds a cell, by its number as Calc shows it.

    Calc keeps a run of like rows as one element, with the number of times it repeats, so the
    numbers count each time.
    """
    number = 1
    for row in sheet.iter(f"{_TABLE}table-row"):
        repeated = int(row.get(f"{_TABLE}number-rows-repeated", "1"))
        cells = _cells(row)
        if cells:
            for each in range(repeated):
                yield number + each, cells
        number += repeated


def _cells(row: ElementTree.Element) -> _Row:
    """Each cell of a row that holds a value or text, by its column, counted from 0.

    Calc keeps a run of like cells as one element, with the number of times it repeats.
    """
    held: _Row = {}
    column = 0
    for element in row:
        repeated = int(element.get(f"{_TABLE}number-columns-repeated", "1"))
        text = "\n".join(
            "".join(paragraph.itertext()) for paragraph in element.iter(f"{_TEXT}p")
        )
        value = element.get(f"{_OFFICE}value")
        if text or value is not None:
            cell = _Cell(element.get(f"{_OFFICE}value-type", ""), value, text)
            held.update((column + each, cell) for each in range(repeated))
        column += repeated
    return held


def _line(
    where: str,
    description: _Cell | None,
    price: _Cell | None,
    quantity: _Cell | None,
) -> Line:
    """The Line of the row that `where` names, or a Refusal naming the cell to fix."""
    if description is None:
        raise Refusal(
            f"{where}: the description is empty. Type what the line is for, such as Payroll."
        )
    return Line(description.text, _price(where, price), _quantity(where, quantity))


def _price(where: str, cell: _Cell | None) -> Decimal:
    """The price of the row that `where` names, to the cent, or a Refusal naming the row."""
    if cell is None:
        raise Refusal(f"{where}: the price is empty. {_PRICE}")
    price = cell.number()
    if price is None:
        raise Refusal(f'{where}: the price "{cell.text}" isn\'t a number. {_PRICE}')
    if price != price.quantize(_CENT):
        raise Refusal(
            f"{where}: the price is {cell.value}, beyond the cent, though Calc may show it"
            f" rounded. {_PRICE}"
        )
    return price.quantize(_CENT)


def _quantity(where: str, cell: _Cell | None) -> int:
    """The quantity of the row that `where` names, or a Refusal naming the row."""
    if cell is None:
        raise Refusal(f"{where}: the quantity is empty. {_QUANTITY}")
    quantity = cell.number()
    if quantity is None:
        raise Refusal(
            f'{where}: the quantity "{cell.text}" isn\'t a number. {_QUANTITY}'
        )
    if quantity != quantity.to_integral_value() or quantity < 1:
        raise Refusal(
            f"{where}: the quantity {cell.value} isn't a whole number from 1. {_QUANTITY}"
        )
    return int(quantity)
