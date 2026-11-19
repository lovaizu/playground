"""What the tests share: .ods sheets built as Calc saves them, the guide's Nordwind sheet and
page, and a stand-in for the `lp` printing command that records what it got."""

import json
import os
import re
import stat
import zipfile
from decimal import ROUND_HALF_UP, Decimal
from xml.sax.saxutils import escape, quoteattr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE = os.path.join(ROOT, "docs", "print-an-invoice.md")

NOTHING_PRINTED = "Nothing was printed. Fix the sheet, save it, and run the command again."
FIX_THE_RATE = "Nothing was printed. Fix the rate and run the command again."
FIX_THE_PRINTER = "Nothing was printed. Set up the printer and run the command again."
SET_A_PRINTER = "set a default printer in Settings, then Printers, and check that `lpstat -d` shows it"

NORDWIND_DETAILS = [
    ["Invoice number", "2026-041"],
    ["Date", ("date", "2026-11-19")],
    ["Client name", "Nordwind Handel GmbH"],
    ["Client address", "Hafenweg 12, 20457 Hamburg"],
    ["Our name", "Lindqvist Buchhaltung GmbH"],
    ["Our address", "Hauptstraße 5, 10115 Berlin"],
    ["Our VAT ID", "DE123456789"],
]
HEADER = ["Description", "Price", "Quantity"]
NORDWIND_LINES = [
    ["Bookkeeping hours", Decimal("80.00"), 10],
    ["Annual accounts", Decimal("350.00"), 1],
    ["Travel to client", Decimal("25.50"), 2],
]


def month_lines():
    """A month of Nordwind's bookkeeping as accounting keeps it: 60 lines, two for each day of
    November, hours of bookkeeping, some of them half hours, and the receipts filed that day."""
    hours = [Decimal("2.5"), 3, Decimal("1.5"), 4, 2]
    receipts = [12, 20, 7]
    lines = []
    for day in range(1, 31):
        lines.append([f"Bookkeeping 11-{day:02}", Decimal("80.00"), hours[day % len(hours)]])
        lines.append([f"Receipts filed 11-{day:02}", Decimal("0.35"), receipts[day % len(receipts)]])
    return lines


# The most rows one printed A4 sheet of plain text holds: 70, at lp's 6 rows an inch on its
# 11.7 inches, before any margin.
ROWS_ON_ONE_SHEET = 70


def totals_of(lines, rate=Decimal("0.19")):
    """The subtotal, the tax, and the total of lines, each a list of description, price, and
    quantity, as the page figures them: each amount the quantity times the price, both to the
    cent half up, the subtotal their sum, and the tax rounded to the cent half up."""
    cent = Decimal("0.01")
    subtotal = sum(
        (
            (Decimal(price).quantize(cent, rounding=ROUND_HALF_UP) * Decimal(quantity)).quantize(
                cent, rounding=ROUND_HALF_UP
            )
            for _, price, quantity in lines
        ),
        Decimal(0),
    )
    tax = (subtotal * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return subtotal, tax, subtotal + tax


def nordwind_rows(lines=None, details=None, header=None):
    """The rows of the guide's `nordwind-2026-11.ods`, rows 1 to 12, with the lines, the details,
    or the header given in place of the guide's."""
    return (
        [list(row) for row in (NORDWIND_DETAILS if details is None else details)]
        + [[]]
        + [list(HEADER if header is None else header)]
        + [list(row) for row in (NORDWIND_LINES if lines is None else lines)]
    )


def guide_page():
    """The page that the guide's Walkthrough shows the printer printing."""
    with open(GUIDE, encoding="utf-8") as guide:
        text = guide.read()
    return re.search(r"```text\n(.*?)\n```", text, re.S).group(1)


MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" \
manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.3" \
manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""

CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content \
xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" \
xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" \
xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.3">
<office:body><office:spreadsheet>{tables}</office:spreadsheet></office:body>
</office:document-content>
"""


def _cell(value):
    if value is None:
        return "<table:table-cell/>"
    if isinstance(value, tuple) and value[0] == "date":
        return (
            f'<table:table-cell office:value-type="date" office:date-value={quoteattr(value[1])}>'
            f"<text:p>{escape(value[1])}</text:p></table:table-cell>"
        )
    if isinstance(value, tuple) and value[0] == "currency":
        return (
            '<table:table-cell office:value-type="currency" office:currency="EUR" '
            f"office:value={quoteattr(value[1])}><text:p>{escape(value[2])}</text:p></table:table-cell>"
        )
    if isinstance(value, tuple) and value[0] == "percentage":
        return (
            f'<table:table-cell office:value-type="percentage" office:value={quoteattr(value[1])}>'
            f"<text:p>{escape(value[2])}</text:p></table:table-cell>"
        )
    if isinstance(value, (int, Decimal, float)) and not isinstance(value, bool):
        number = Decimal(str(value))
        shown = f"{number:.2f}" if isinstance(value, Decimal) else str(value)
        return (
            f'<table:table-cell office:value-type="float" office:value="{number.normalize():f}">'
            f"<text:p>{shown}</text:p></table:table-cell>"
        )
    return (
        f'<table:table-cell office:value-type="string"><text:p>{escape(str(value))}</text:p>'
        "</table:table-cell>"
    )


def _row(cells):
    """A row as Calc writes it: a run of empty cells as one repeated cell, and the rest of the
    row's 1024 columns as one repeated empty cell."""
    out = []
    empty = 0
    for value in cells:
        if value is None:
            empty += 1
            continue
        if empty:
            out.append(f'<table:table-cell table:number-columns-repeated="{empty}"/>')
            empty = 0
        out.append(_cell(value))
    rest = 1024 - len(cells) + empty
    out.append(f'<table:table-cell table:number-columns-repeated="{rest}"/>')
    return f"<table:table-row>{''.join(out)}</table:table-row>"


def _table(name, rows):
    """A sheet as Calc writes it: a run of empty rows as one repeated row, and the rest of the
    sheet's rows as one repeated empty row."""
    out = []
    empty = 0
    for cells in rows:
        if not any(value is not None for value in cells):
            empty += 1
            continue
        if empty:
            out.append(
                f'<table:table-row table:number-rows-repeated="{empty}">'
                '<table:table-cell table:number-columns-repeated="1024"/></table:table-row>'
            )
            empty = 0
        out.append(_row(cells))
    out.append(
        f'<table:table-row table:number-rows-repeated="{1048576 - len(rows) + empty}">'
        '<table:table-cell table:number-columns-repeated="1024"/></table:table-row>'
    )
    return f"<table:table table:name={quoteattr(name)}>{''.join(out)}</table:table>"


def write_ods(path, rows, more_sheets=()):
    """Writes an .ods file at path as Calc saves it: its first sheet holds rows, each a list of
    cells, where a str is a text cell, an int or Decimal a number cell, a tuple of the word date
    and the day as YYYY-MM-DD a date cell, a tuple of the word currency or percentage, the value
    Calc stores, and the text Calc shows a Currency or Percent cell, and None an empty cell; each
    of more_sheets, a list of rows, follows it."""
    tables = _table("Sheet1", rows) + "".join(
        _table(f"Sheet{n}", more) for n, more in enumerate(more_sheets, start=2)
    )
    with zipfile.ZipFile(path, "w") as ods:
        ods.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/vnd.oasis.opendocument.spreadsheet",
            compress_type=zipfile.ZIP_STORED,
        )
        ods.writestr("META-INF/manifest.xml", MANIFEST, compress_type=zipfile.ZIP_DEFLATED)
        ods.writestr(
            "content.xml", CONTENT.format(tables=tables), compress_type=zipfile.ZIP_DEFLATED
        )
    return path


def repeat_row(path, first_text, times):
    """Rewrites the .ods file at path as Calc saves a row copied down: the row whose first cell
    holds first_text is written once with table:number-rows-repeated of times, and so stands for
    that many rows, pushing each row under it down."""
    with zipfile.ZipFile(path) as ods:
        xml = ods.read("content.xml").decode("utf-8")
    start = f'<table:table-row><table:table-cell office:value-type="string"><text:p>{escape(first_text)}</text:p>'
    if xml.count(start) != 1:
        raise ValueError(f"no one row starts with {first_text!r}")
    xml = xml.replace(
        start, start.replace("<table:table-row>", f'<table:table-row table:number-rows-repeated="{times}">')
    )
    with zipfile.ZipFile(path, "w") as ods:
        ods.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.oasis.opendocument.spreadsheet")
        ods.writestr("META-INF/manifest.xml", MANIFEST, compress_type=zipfile.ZIP_DEFLATED)
        ods.writestr("content.xml", xml, compress_type=zipfile.ZIP_DEFLATED)
    return path


LP = """#!{python}
import json, os, sys
args = sys.argv[1:]
sys.stderr.write({says!r})
files = [a for a in args if not a.startswith("-") and os.path.isfile(a)]
if files:
    with open(files[-1], encoding="utf-8") as given:
        text = given.read()
else:
    text = sys.stdin.buffer.read().decode("utf-8")
record = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lp-record.json")
with open(record, "w", encoding="utf-8") as out:
    json.dump({{"args": args, "text": text}}, out)
sys.exit({status})
"""


def put_lp(folder, status=0, says="", python="/usr/bin/env python3"):
    """Puts a stand-in `lp` in folder that records its arguments and the text it was given to
    `lp-record.json` beside it, writes says to its standard error, and exits with status. It reads
    the page as UTF-8, as print_page hands it, whatever the machine's locale."""
    path = os.path.join(folder, "lp")
    with open(path, "w", encoding="utf-8") as script:
        script.write(LP.format(python=python, status=status, says=says))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def lp_record(folder):
    """What the stand-in `lp` in folder got, as a dict of the arguments under args and the text
    under text, or None where it never ran."""
    path = os.path.join(folder, "lp-record.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as record:
        return json.load(record)
