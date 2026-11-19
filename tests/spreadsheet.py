"""The .ods files that the tests build, as LibreOffice Calc saves them, and the walkthrough's values.

A row is a list of cells. A cell is None where Calc keeps it empty, a str for text, an int or a
Decimal for a number, or a Cell for a currency, a formula, or text in parts.
"""

from __future__ import annotations

import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Union
from xml.sax.saxutils import escape, quoteattr

MIMETYPE = "application/vnd.oasis.opendocument.spreadsheet"


@dataclass(frozen=True)
class Cell:
    """A cell that Calc saves with more than its value: a currency, a formula, or text in parts.

    `kind` is the office:value-type, `value` the office:value of a number, `shown` the text
    that Calc shows, `formula` the formula or "", and `parts` the spans of the text or ().
    """

    kind: str
    value: str = ""
    shown: str = ""
    formula: str = ""
    parts: Sequence[str] = ()


Value = Union[None, str, int, Decimal, Cell]

WALKTHROUGH_ROWS: list[list[Value]] = [
    ["Description", "Price", "Quantity"],
    ["Bookkeeping, October", Decimal("85.00"), 12],
    ["Payroll, October", Decimal("14.50"), 9],
    ["Annual accounts 2025", Decimal("450.00"), 1],
]

# The README's walkthrough, in the terminal, with the date of the day it runs.
WALKTHROUGH_INVOICE = """\
Invoice 2026-031
Client: Nordwind GmbH
Date: {today}
Tax rate: 19%

Bookkeeping, October               1020.00 EUR
Payroll, October                    130.50 EUR
Annual accounts 2025                450.00 EUR
Subtotal                           1600.50 EUR
Tax                                 304.10 EUR
Total                              1904.60 EUR"""

WALKTHROUGH_ARGS = [
    "October.ods",
    "--client",
    "Nordwind GmbH",
    "--number",
    "2026-031",
    "--rate",
    "19",
]

SENT = "Sent to your default printer."


def currency(amount: str) -> Cell:
    """A price that Calc keeps in its currency format, such as 85.00 EUR."""
    return Cell(
        "currency", value=_number(Decimal(amount)), shown=f"{Decimal(amount):.2f} EUR"
    )


def formula(amount: str, text: str) -> Cell:
    """A number that a formula, such as of:=80+5, gives."""
    return Cell("float", value=_number(Decimal(amount)), shown=amount, formula=text)


def spans(*parts: str) -> Cell:
    """Text that Calc keeps in spans, as where part of it has its own format."""
    return Cell("string", parts=parts)


def write(
    path: str,
    rows: Sequence[Sequence[Value]],
    others: Sequence[Sequence[Sequence[Value]]] = (),
    blank_rows_after: int = 1048570,
) -> None:
    """Writes an .ods file at `path` whose first sheet holds `rows`, row 1 first.

    `others` are the sheets after the first. Calc ends a sheet with its blank rows as one
    repeated row, so the first sheet ends with `blank_rows_after` of them.
    """
    sheets = [_sheet("Sheet1", rows, blank_rows_after)]
    sheets += [_sheet(f"Sheet{n}", each, 0) for n, each in enumerate(others, start=2)]
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<office:document-content"
        ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
        ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
        ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
        ' xmlns:calcext="urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0"'
        ' xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2"'
        ' office:version="1.3">'
        "<office:body><office:spreadsheet>"
        + "".join(sheets)
        + "</office:spreadsheet></office:body></office:document-content>"
    )
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"'
        ' manifest:version="1.3">'
        f'<manifest:file-entry manifest:full-path="/" manifest:version="1.3"'
        f' manifest:media-type="{MIMETYPE}"/>'
        '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
        "</manifest:manifest>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            zipfile.ZipInfo("mimetype"), MIMETYPE, compress_type=zipfile.ZIP_STORED
        )
        archive.writestr(
            "META-INF/manifest.xml", manifest, compress_type=zipfile.ZIP_DEFLATED
        )
        archive.writestr("content.xml", content, compress_type=zipfile.ZIP_DEFLATED)


def _sheet(name: str, rows: Sequence[Sequence[Value]], blank_rows_after: int) -> str:
    """The table:table of one sheet, its blank rows run together as Calc writes them."""
    width = max((len(row) for row in rows), default=1)
    out = [f"<table:table table:name={quoteattr(name)}>"]
    out.append(f'<table:table-column table:number-columns-repeated="{width}"/>')
    blank = 0
    for row in rows:
        if all(cell is None for cell in row):
            blank += 1
            continue
        out.append(_blank_rows(blank, width))
        blank = 0
        out.append(
            "<table:table-row>"
            + "".join(_cell(cell) for cell in row)
            + "</table:table-row>"
        )
    out.append(_blank_rows(blank + blank_rows_after, width))
    out.append("</table:table>")
    return "".join(out)


def _blank_rows(count: int, width: int) -> str:
    """`count` blank rows as one repeated row, or "" for none."""
    if not count:
        return ""
    return (
        f'<table:table-row table:number-rows-repeated="{count}">'
        f'<table:table-cell table:number-columns-repeated="{width}"/></table:table-row>'
    )


def _cell(cell: Value) -> str:
    """The table:table-cell of one cell."""
    if cell is None:
        return "<table:table-cell/>"
    if isinstance(cell, str):
        return _text_cell(escape(cell))
    if isinstance(cell, Cell):
        return _kept_cell(cell)
    shown = f"{cell:.2f}" if isinstance(cell, Decimal) else str(cell)
    return (
        f'<table:table-cell office:value-type="float" office:value="{_number(Decimal(cell))}"'
        f' calcext:value-type="float"><text:p>{shown}</text:p></table:table-cell>'
    )


def _text_cell(inner: str) -> str:
    """A text cell holding the XML `inner`."""
    return (
        '<table:table-cell office:value-type="string" calcext:value-type="string">'
        f"<text:p>{inner}</text:p></table:table-cell>"
    )


def _kept_cell(cell: Cell) -> str:
    """The table:table-cell of a Cell."""
    if cell.kind == "string":
        return _text_cell(
            "".join(f"<text:span>{escape(part)}</text:span>" for part in cell.parts)
        )
    held = f" table:formula={quoteattr(cell.formula)}" if cell.formula else ""
    money = ' office:currency="EUR"' if cell.kind == "currency" else ""
    return (
        f'<table:table-cell{held} office:value-type="{cell.kind}"{money}'
        f' office:value="{cell.value}" calcext:value-type="{cell.kind}">'
        f"<text:p>{escape(cell.shown)}</text:p></table:table-cell>"
    )


def _number(amount: Decimal) -> str:
    """The office:value of a number, as Calc writes it, with no trailing zero."""
    return format(amount.normalize(), "f")
