"""The colleague's printed invoice: its layout, and the rounding to the cent of each figure it
prints but the tax, whose rounding tax.py decides, so that the page always adds up."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Union

from invoicer.lines import Line
from invoicer.sheet import Details
from invoicer.tax import CENT, tax_of

# The Description column's width; each other column is right-aligned after a gap.
DESCRIPTION_WIDTH = 20
# Every invoice is in EUR; neither the sheet nor the command carries a currency.
_CURRENCY = "EUR"
# The table's header row, a name for each column.
_HEADER = ("Description", "Quantity", "Unit price", "Amount")


def render_page(details: Details, lines: list[Line], rate: Decimal) -> str:
    """Gives the page's text, every invoice in EUR: the details, a header row, each line with its
    quantity, unit price, and amount, then the Subtotal, the tax as `Tax 19%`, and the Total,
    ending with a newline.

    Takes: details and lines as sheet.read_sheet gives them, and rate as the fraction that
    rate.parse_rate gives, such as Decimal('0.19') for 19%.

    Figures: each unit price shows to the cent, rounded half up, as Calc shows it; each amount is
    the quantity times that shown price, rounded half up to the cent; the Subtotal is the sum of
    the shown amounts, the tax is tax.tax_of on it, and the Total their sum, so the page's figures
    always add up. A whole quantity shows as a whole number, such as 10, and a fraction as it is,
    such as 2.5.

    Layout: a description longer than its column, DESCRIPTION_WIDTH characters, wraps onto the
    next rows of that column, between words, and a word longer than the column breaks at its
    width; a description exactly as wide stays on one row. The money columns widen to the
    longest figure, so no text is cut."""
    line_cells = [_line_cells(line) for line in lines]
    totals = _totals([_amount(line) for line in lines], rate)
    columns = _Columns.fitting(line_cells, [figure for _, figure in totals])
    rows = (
        _details_rows(details)
        + _table_rows(line_cells, columns)
        + [""]
        + _totals_rows(totals, columns)
    )
    return "\n".join(rows) + "\n"


# The text of a line's cells on the page: description, quantity, unit price, and amount.
_LineCells = tuple[str, str, str, str]


def _line_cells(line: Line) -> _LineCells:
    """The line's description, its quantity as shown, and its unit price and amount in EUR."""
    return (
        line.description,
        _shown_quantity(line.quantity),
        _money(_unit_price(line)),
        _money(_amount(line)),
    )


def _unit_price(line: Line) -> Decimal:
    """The line's price as the page shows it, to the cent, rounded half up, as Calc shows it."""
    return _cents(line.price)


def _amount(line: Line) -> Decimal:
    """The line's quantity times its shown unit price, rounded half up to the cent."""
    return _cents(_unit_price(line) * line.quantity)


def _totals(amounts: list[Decimal], rate: Decimal) -> list[tuple[str, str]]:
    """The Subtotal, the tax, and the Total, each with its label, in EUR: the Subtotal the sum
    of the shown amounts, the tax tax.tax_of on it, and the Total their sum."""
    # Starts at 0.00, where totals.py starts at Decimal(0), so a page without lines still shows
    # its Subtotal to the cent, as 0.00 EUR.
    subtotal = sum(amounts, Decimal("0.00"))
    tax = tax_of(subtotal, rate)
    percent = f"{(rate * 100).normalize():f}"
    return [
        ("Subtotal", _money(subtotal)),
        (f"Tax {percent}%", _money(tax)),
        ("Total", _money(subtotal + tax)),
    ]


@dataclass
class _Columns:
    """The widths of the Quantity, Unit price, and Amount columns, which follow the Description
    column of DESCRIPTION_WIDTH."""

    quantity: int
    price: int
    amount: int

    @classmethod
    def fitting(cls, line_cells: list[_LineCells], total_figures: list[str]) -> _Columns:
        """Each column as wide as the widest of its header name and the texts under it, the
        totals' figures standing in the Amount column."""
        _, quantity, price, amount = _HEADER
        return cls(
            quantity=max(len(text) for text in [quantity] + [cells[1] for cells in line_cells]),
            price=max(len(text) for text in [price] + [cells[2] for cells in line_cells]),
            amount=max(
                len(text) for text in [amount] + [cells[3] for cells in line_cells] + total_figures
            ),
        )

    def row(self, description: str, quantity: str, price: str, amount: str) -> str:
        """A row of the table, the description left-aligned and each other cell right-aligned in
        its column, after its gap."""
        return (
            f"{description:<{DESCRIPTION_WIDTH}}  {quantity:>{self.quantity}}"
            f"    {price:>{self.price}}    {amount:>{self.amount}}"
        )

    def page_width(self) -> int:
        """The width of a row of the table, to whose right edge the totals align."""
        # Each cell pads to its column's width, so a row of empty cells is as wide as any row.
        return len(self.row("", "", "", ""))


def _table_rows(line_cells: list[_LineCells], columns: _Columns) -> list[str]:
    """The header row, then each line's row, its description wrapped onto the next rows of its
    column where longer than DESCRIPTION_WIDTH."""
    rows = [columns.row(*_HEADER)]
    for description, quantity, price, amount in line_cells:
        # Off, so a hyphenated word longer than the column breaks at the column's width as any
        # word does, not at its hyphen.
        wrapped = textwrap.wrap(description, DESCRIPTION_WIDTH, break_on_hyphens=False)
        # wrapped is never empty, as sheet.py refuses a description that's empty or of spaces.
        rows.append(columns.row(wrapped[0], quantity, price, amount))
        rows.extend(wrapped[1:])
    return rows


def _totals_rows(totals: list[tuple[str, str]], columns: _Columns) -> list[str]:
    """A row for each total, its label at the left and its figure at the table's right edge."""
    width = columns.page_width()
    return [f"{label}{figure:>{width - len(label)}}" for label, figure in totals]


def _details_rows(details: Details) -> list[str]:
    """The page's opening: who bills, whom, and the invoice's number and date, each block
    followed by an empty row."""
    return [
        details.our_name,
        details.our_address,
        f"VAT ID {details.our_vat_id}",
        "",
        details.client_name,
        details.client_address,
        "",
        f"Invoice {details.invoice_number}",
        f"Date {details.date}",
        "",
    ]


def _cents(value: Decimal) -> Decimal:
    """The value rounded half up to the cent, such as 400.333 -> 400.33 and 0.125 -> 0.13."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _shown_quantity(value: Union[int, Decimal]) -> str:
    """An int as its digits, such as 10, and a Decimal in plain notation, such as 2.5, never in
    exponent form, such as 1E+1."""
    return f"{value:f}" if isinstance(value, Decimal) else str(value)


def _money(figure: Decimal) -> str:
    """The figure as the page shows money, such as `80.00 EUR`."""
    return f"{figure:f} {_CURRENCY}"
