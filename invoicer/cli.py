"""The run that each command line asks for, from the values it takes to its exit status.

It alone turns the typed rate into Details' fraction, holds the sample's lines and details,
dates each invoice today, and writes to the terminal.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence


def main(argv: Sequence[str]) -> int:
    """One run of invoicer, as its command line asks.

    Takes: the arguments after `invoicer`: a file with `--client`, `--number`, and `--rate`, or
    `--sample` alone.
    Gives: 0 once the invoice shows and the printer has taken it, and 1 for each refusal.
    Changes: writes the invoice and then that it went to the default printer, or the refusal,
    to the terminal; and has the printer print the invoice.
    Refuses, before it reads any file, writing what to fix: a run with no file and no
    `--sample`, naming the file it needs; `--sample` with a file or values, naming what to
    leave out; and an empty client or number, or a rate that isn't a number from 0 to 100,
    naming the value. It then writes each Refusal that the spreadsheet reader or the printer
    raises, with the Requirement to check.
    """
    raise NotImplementedError("cli.main")


def run() -> None:
    """The console script `invoicer`: main on the command line, exiting with its status."""
    sys.exit(main(sys.argv[1:]))
