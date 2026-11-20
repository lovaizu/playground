"""The command that the accounting team runs, `python3 -m invoicer <spreadsheet.ods> --tax-rate
<percent>`: its arguments, the tax rate as a percent, and how a refusal is written and ends the
run."""

from __future__ import annotations

import sys
from decimal import Decimal, InvalidOperation
from typing import TextIO

from invoicer.render import render
from invoicer.sheet import SheetError, read_lines

_RATE_OPTION = "--tax-rate"
_USAGE = (
    f"usage: python3 -m invoicer <spreadsheet.ods> {_RATE_OPTION} <percent>,"
    f" such as invoice.ods {_RATE_OPTION} 19"
)


class _WrongArgument(Exception):
    """A wrong argument, its message saying what to fix."""


def main(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    """Runs the command on argv, the arguments after the program's name:
    `<spreadsheet.ods> --tax-rate <percent>`, the percent 0 or a number from 1 to 100 written as
    19, 7.5, or 19%; a rate over 0 and under 1, such as 0.19, is refused as a fraction written
    for a percent.

    Writes the invoice of the spreadsheet's lines at that rate to stdout, ending with a newline,
    and gives 0. Where an argument is wrong or the spreadsheet refused, as read_lines refuses,
    writes one line `invoicer: <what to fix>` to stderr and nothing to stdout, and gives 2; the
    rate is checked before the spreadsheet is read."""
    try:
        path, rate = _arguments(argv)
        lines = read_lines(path)
    except (_WrongArgument, SheetError) as refusal:
        stderr.write(f"invoicer: {refusal}\n")
        return 2
    stdout.write(render(lines, rate) + "\n")
    return 0


def _arguments(argv: list[str]) -> tuple[str, Decimal]:
    """The spreadsheet's path, and the rate as the fraction that render takes."""
    if len(argv) != 3 or argv[1] != _RATE_OPTION:
        raise _WrongArgument(_USAGE)
    return argv[0], _rate(argv[2])


def _rate(given: str) -> Decimal:
    """The fraction of a percent written as 19, 7.5, or 19%, 0 or from 1 to 100: no client's rate
    lies over 0 and under 1 %, so such a rate is taken as a fraction written by mistake."""
    number = given.removesuffix("%")
    try:
        percent = Decimal(number)
        # Decimal reads "NaN" as a number, and comparing it raises InvalidOperation too.
        within = 0 <= percent <= 100
    except InvalidOperation:
        within = False
    if not within:
        raise _WrongArgument(
            f'{_RATE_OPTION} must be a percent from 0 to 100, such as 19, 7.5, or 19%, not "{given}"'
        )
    if 0 < percent < 1:
        # normalize drops the zeros that 0.19 * 100 leaves, 19.00, and :f keeps 0.1 * 100 from 1E+1.
        meant = f"{(percent * 100).normalize():f}"
        raise _WrongArgument(
            f'{_RATE_OPTION} is a percent, so "{given}" would be {number} %; write {meant} for {meant} %'
        )
    return percent / 100


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout, sys.stderr))
