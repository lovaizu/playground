"""How the tests build the .ods files they read, as Calc saves them: a zip whose first member is the
mimetype, and whose content.xml holds the sheets."""

from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from decimal import Decimal
from xml.sax.saxutils import escape, quoteattr

MIMETYPE = "application/vnd.oasis.opendocument.spreadsheet"
# The header row of a sheet laid out as the guide says.
HEADER = ["Description", "Price", "Quantity"]

_CONTENT = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<office:document-content'
    ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
    ' xmlns:xlink="http://www.w3.org/1999/xlink"'
    ' office:version="1.3">'
    "<office:body><office:spreadsheet>{tables}</office:spreadsheet></office:body>"
    "</office:document-content>"
)


class Currency:
    """A currency cell: its stored value, the text Calc shows for it, and its currency."""

    def __init__(self, value: str, shown: str, currency: str = "EUR"):
        self.value = value
        self.shown = shown
        self.currency = currency


def cell(value) -> str:
    """The XML of one cell: None is empty, a str is text, an int or Decimal is a number, and a
    Currency is a currency cell."""
    if value is None:
        return "<table:table-cell/>"
    if isinstance(value, str):
        return f'<table:table-cell office:value-type="string"><text:p>{escape(value)}</text:p></table:table-cell>'
    if isinstance(value, Currency):
        return (
            f'<table:table-cell office:value-type="currency" office:currency={quoteattr(value.currency)}'
            f" office:value={quoteattr(value.value)}><text:p>{escape(value.shown)}</text:p>"
            "</table:table-cell>"
        )
    shown = str(Decimal(value))
    return (
        f'<table:table-cell office:value-type="float" office:value="{shown}">'
        f"<text:p>{shown}</text:p></table:table-cell>"
    )


def row(cells) -> str:
    """The XML of one row of the cells; a row of no cells is an empty row, and a str is the XML of a
    row as given, for a row that Calc saves with repeated, merged, or formatted cells."""
    if isinstance(cells, str):
        return cells
    if not cells:
        return "<table:table-row><table:table-cell/></table:table-row>"
    return "<table:table-row>" + "".join(cell(each) for each in cells) + "</table:table-row>"


def table(rows, name: str = "Sheet1") -> str:
    """The XML of one sheet of the rows."""
    return f"<table:table table:name={quoteattr(name)}>" + "".join(row(r) for r in rows) + "</table:table>"


def write_tables(path: str, tables_xml: str, mimetype: str = MIMETYPE) -> str:
    """Writes an .ods file at the path whose sheets are the tables' XML, and gives the path."""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), mimetype, compress_type=zipfile.ZIP_STORED)
        archive.writestr("content.xml", _CONTENT.format(tables=tables_xml), zipfile.ZIP_DEFLATED)
    return path


def write_rows(path: str, rows) -> str:
    """Writes an .ods file at the path with one sheet of the rows, and gives the path."""
    return write_tables(path, table(rows))


class Folder(unittest.TestCase):
    """A test with a temporary folder of its own, removed when the test ends."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def path(self, name: str) -> str:
        """The path of a file of that name in the test's folder."""
        return os.path.join(self.folder, name)

    def sheet(self, rows, name: str = "invoice.ods") -> str:
        """Writes an .ods file of one sheet of the rows in the test's folder, and gives its path."""
        return write_rows(self.path(name), rows)
