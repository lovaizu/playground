"""What the `invoicer` command takes from whoever runs it, and what it prints."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from invoicer.lines import ROW, LineError, parse_lines
from invoicer.render import render


def main(argv: Sequence[str] | None = None) -> None:
    """Runs `invoicer LINES --rate PERCENT`, the entry point that pyproject.toml installs.

    Takes: the command line after `invoicer`, or the process's own where None. LINES is the path
    of a file saved from a spreadsheet as UTF-8 text, a byte order mark allowed, of one row for each
    line, `<description>;<price>;<quantity>`, as `invoicer.lines.parse_lines` reads it. PERCENT is
    the tax rate in percent, from 0 to 100, with or without `%`, such as `19` or `7.7%`.
    Gives: nothing; prints to standard output the invoice text that `invoicer.render` gives for
    the lines at the rate.
    Refuses: SystemExit with code 2, printing nothing to standard output, and to standard error
    the usage and `invoicer: error: <what's wrong>`, where --rate is missing or isn't a percent
    from 0 to 100, the file doesn't exist or isn't UTF-8 text, it holds no line, or a row is wrong,
    with the row's number.
    """
    parser = _parser()
    arguments = parser.parse_args(argv)
    path = arguments.lines
    try:
        # utf-8-sig drops the byte order mark that a spreadsheet's CSV UTF-8 starts with.
        with open(path, encoding="utf-8-sig") as saved:
            lines = parse_lines(saved.read())
    except FileNotFoundError:
        parser.error(
            f"{path}: no such file; give the path of the file of lines saved from the spreadsheet"
        )
    except UnicodeDecodeError:
        parser.error(f"{path}: not saved as UTF-8 text; save it from the spreadsheet as CSV UTF-8")
    except LineError as wrong:
        parser.error(f"{path}, {wrong}")
    if not lines:
        parser.error(f"{path}: holds no line; each row must be {ROW}")
    print(render(lines, arguments.rate))


def _parser() -> argparse.ArgumentParser:
    """The command line that `main` takes, with the help that `invoicer --help` prints."""
    parser = argparse.ArgumentParser(
        prog="invoicer",
        description="Prints the invoice of the lines saved from a spreadsheet, at a tax rate.",
    )
    parser.add_argument(
        "lines",
        metavar="LINES",
        help="the file saved from the spreadsheet as CSV UTF-8 with semicolons, one row for each "
        f"line: {ROW}",
    )
    parser.add_argument(
        "--rate",
        required=True,
        type=_rate,
        metavar="PERCENT",
        help="the client's tax rate in percent, such as 19 or 7.7",
    )
    return parser


def _rate(percent: str) -> Decimal:
    """The tax rate as the fraction that `invoicer.render` takes, of a percent from 0 to 100
    written with or without `%`; argparse names the option in the refusal."""
    try:
        value = Decimal(percent.removesuffix("%"))
    except InvalidOperation:
        value = None
    if value is None or not value.is_finite() or not 0 <= value <= 100:
        raise argparse.ArgumentTypeError(
            "the tax rate must be a percent from 0 to 100, written with a point, "
            f"such as 19 or 7.7, not {percent!r}"
        )
    return value / 100
