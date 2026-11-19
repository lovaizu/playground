"""The run that each command line asks for, from the values it takes to its exit status.

It alone turns the typed rate into Details' fraction, holds the sample's lines and details,
dates each invoice today, and writes to the terminal.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from invoicer import invoice, ods, printer
from invoicer.invoice import Details
from invoicer.lines import Line
from invoicer.refusal import Refusal

_OPTIONS = ("--client", "--number", "--rate")
_EXAMPLE = (
    'such as: invoicer October.ods --client "Nordwind GmbH" --number 2026-031 --rate 19'
)
_RATE = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_SAMPLE_LINES = [Line("Sample service", Decimal("100.00"), 1)]
_SAMPLE = Details("Sample client", "SAMPLE", "19", Decimal(19) / 100)
_SENT = "Sent to your default printer."


def main(argv: Sequence[str]) -> int:
    """One run of invoicer, as its command line asks.

    Takes: the arguments after `invoicer`: a file with `--client`, `--number`, and `--rate`, or
    `--sample` alone.
    Gives: 0 once the invoice shows and the printer has taken it, and 1 for each refusal.
    Changes: writes the invoice and then that it went to the default printer, or the refusal,
    to the terminal; and has the printer print the invoice.
    Refuses, before it reads any file, writing what to fix: a run with no file and no
    `--sample`, naming the file it needs; `--sample` with a file or values, naming what to
    leave out; an empty or missing client or number, or a rate that isn't a number from 0 to
    100, naming the option; and an option that invoicer lacks, one given twice, or one with no
    value after it, naming the option. It then writes each Refusal that the spreadsheet reader
    or the printer raises, with the Requirement to check.
    """
    try:
        file, details = _given(argv)
        lines = _SAMPLE_LINES if file is None else ods.read(file)
    except Refusal as refusal:
        return _refused(refusal)
    made = invoice.make(lines, details, date.today())
    print(f"{made.text}\n", flush=True)
    try:
        printer.send(made)
    except Refusal as refusal:
        return _refused(refusal)
    print(_SENT)
    return 0


def run() -> None:
    """The console script `invoicer`: main on the command line, exiting with its status."""
    sys.exit(main(sys.argv[1:]))


def _given(argv: Sequence[str]) -> tuple[str | None, Details]:
    """The file and the details that the command line gives, with None as the file of the sample.

    Raises Refusal, naming what to fix, where the command line isn't a file with the three
    values, or `--sample` alone.
    """
    files: list[str] = []
    values: dict[str, str] = {}
    sample = False
    rest = list(argv)
    while rest:
        word = rest.pop(0)
        if word == "--sample":
            sample = True
        elif word in _OPTIONS:
            if not rest:
                raise Refusal(f"{word} has no value. Give it one, {_EXAMPLE}")
            if word in values:
                raise Refusal(f"{word} is given twice. Give it once, {_EXAMPLE}")
            values[word] = rest.pop(0)
        elif word.startswith("-"):
            raise Refusal(
                f"{word} isn't an option of invoicer. Give a file with --client, --number,"
                f" and --rate, {_EXAMPLE}, or --sample alone."
            )
        else:
            files.append(word)
    if sample:
        extras = files + [option for option in _OPTIONS if option in values]
        if extras:
            raise Refusal(
                f"--sample prints the sample alone. Leave out {extras[0]}, or leave out"
                " --sample to print your own invoice."
            )
        return None, _SAMPLE
    if len(files) != 1:
        raise Refusal(
            "give one .ods file of the invoice's lines with the three values, "
            f"{_EXAMPLE}, or --sample alone to print the sample."
        )
    client = _value(values, "--client", 'the client\'s name, such as "Nordwind GmbH"')
    number = _value(values, "--number", "the invoice's number, such as 2026-031")
    rate = values.get("--rate", "")
    if not _RATE.fullmatch(rate) or Decimal(rate) > 100:
        shown = f'"{rate}"' if "--rate" in values else "missing"
        raise Refusal(
            f"--rate is {shown}. Give the client's tax rate in percent, a number from 0 to"
            " 100 with a point for its decimals, such as --rate 19 or --rate 19.5."
        )
    return files[0], Details(client, number, rate, Decimal(rate) / 100)


def _value(values: dict[str, str], option: str, what: str) -> str:
    """The value given for `option`, or a Refusal naming it where it's missing or empty."""
    value = values.get(option, "")
    if not value.strip():
        shown = "empty" if option in values else "missing"
        raise Refusal(f"{option} is {shown}. Give {what}.")
    return value


def _refused(refusal: Refusal) -> int:
    """Writes the refusal and the Requirement it asks to check, and gives the status 1."""
    print(f"invoicer: {refusal.fix}", file=sys.stderr)
    if refusal.check:
        print(f"Check this Requirement of the README: {refusal.check}", file=sys.stderr)
    return 1
