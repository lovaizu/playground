"""What a run tells one from accounting in place of the invoice, so they mend it alone.

The command, the spreadsheet reader, and the printer raise it, and only the command writes it
to the terminal.
"""

from __future__ import annotations


class Refusal(Exception):
    """A stop before anything shows, or the printer's reason once the invoice shows.

    Holds `fix`: the file, column, row, or value to fix, such as
    `row 3: the price "14,50 EUR" isn't a number`, or the printer's reason.
    Holds `check`: the Requirement of the README to check, such as `lpstat -d`, or "" where
    none applies.
    """

    def __init__(self, fix: str, check: str = "") -> None:
        super().__init__(fix)
        self.fix = fix
        self.check = check
