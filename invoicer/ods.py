"""The lines that a Calc .ods file keeps on its first sheet under Description, Price, Quantity."""

from __future__ import annotations

from invoicer.lines import Line


def read(path: str) -> list[Line]:
    """The lines of the .ods file at `path`, in the order of its rows.

    Takes: the path of the file, from the folder the command runs in.
    Gives: one library Line for each row under row 1, its price a Decimal to the cent and its
    quantity a whole number from 1; a row whose three cells are empty gives none.
    Changes: nothing; it only reads the file, with Python's standard library alone.
    Refuses: Refusal naming the first wrong place it meets, each row by its number as Calc shows
    it: the file where it's missing or isn't an .ods file; the column where row 1 lacks
    Description, Price, or Quantity; the row whose price isn't a number to the cent, whose
    quantity isn't a whole number from 1, or that has a price and a quantity but no
    description; and the file where its first sheet holds no line.
    """
    raise NotImplementedError("ods.read")
