"""The `invoicer` command's words and exit statuses: `invoicer print SHEET --rate PERCENT`, which
reads the rate and the sheet whole before anything reaches the printer."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from invoicer.page import render_page
from invoicer.printer import PrintError, print_page
from invoicer.rate import RateError, parse_rate
from invoicer.sheet import SheetError, read_sheet

USAGE = "invoicer print SHEET --rate PERCENT"
FIX_THE_RATE = "Nothing was printed. Fix the rate and run the command again."
FIX_THE_SHEET = "Nothing was printed. Fix the sheet, save it, and run the command again."
FIX_THE_PRINTER = "Nothing was printed. Set up the printer and run the command again."


def main(argv: Optional[list[str]] = None) -> int:
    """Runs the command on argv, the arguments after the command's name, or sys.argv[1:] where
    it's None, every invoice in EUR. It reads the rate, then the sheet, and hands the page to the
    printer only once it has read both whole.

    Gives: 0, with `Printed invoice <number> for <client> on your default printer.` on standard
    output; 1, with the refusal on standard error and under it FIX_THE_RATE for the rate,
    FIX_THE_SHEET for the sheet, and FIX_THE_PRINTER for the printer. Raises SystemExit 2 for
    wrong usage, such as a word other than `print`, no `--rate`, or `--rate` given twice, with the
    usage line on standard error and nothing printed, and SystemExit 0 for `--help`, with the
    usage line on standard output."""
    parser = argparse.ArgumentParser(
        prog="invoicer",
        usage=USAGE,
        description="Prints a client's invoice from your Calc sheet at the client's tax rate.",
    )
    parser.add_argument("command", choices=["print"], help="print the invoice")
    parser.add_argument("sheet", metavar="SHEET", help="the .ods file Calc saved")
    parser.add_argument(
        "--rate",
        metavar="PERCENT",
        required=True,
        action=_OneRate,
        help="the client's tax rate, such as 19",
    )
    args = parser.parse_args(argv)
    try:
        rate = parse_rate(args.rate)
    except RateError as refused:
        return _refuse(refused, FIX_THE_RATE)
    try:
        details, lines = read_sheet(args.sheet)
    except SheetError as refused:
        return _refuse(refused, FIX_THE_SHEET)
    try:
        print_page(render_page(details, lines, rate))
    except PrintError as refused:
        return _refuse(refused, FIX_THE_PRINTER)
    print(f"Printed invoice {details.invoice_number} for {details.client_name} on your default printer.")
    return 0


def _refuse(refused: Exception, fix: str) -> int:
    print(refused, file=sys.stderr)
    print(fix, file=sys.stderr)
    return 1


class _OneRate(argparse.Action):
    """Stores the typed rate, and makes a second `--rate` a usage error, as two rates for one
    invoice don't say which one the colleague meant."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest) is not None:
            parser.error("give the rate once, such as --rate 19")
        setattr(namespace, self.dest, values)
