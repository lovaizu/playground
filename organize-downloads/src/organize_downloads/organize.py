"""Organize planner: which entries directly in the organized folder are to be moved, each with the
type folder it goes to.

Working the moves out apart from making them lets a run show every move before any is made. The
planner only reads the folder, so planning changes nothing.
"""

import os
from pathlib import Path
from typing import NamedTuple

from organize_downloads import type_table


class Move(NamedTuple):
    """A file to be moved: its name directly in the organized folder, and the type folder inside
    that folder it goes to."""

    name: str
    type_folder: str


def plan_moves(folder: Path) -> list[Move]:
    """Take in the organized folder; give back one Move for each file to be moved, sorted by
    name, so a listing is the same on every run.

    Only plain files directly in the folder are moved. Left in place are folders, the type folders
    among them, and what is inside them; symbolic links, whatever they point to; other entries
    that are neither a plain file nor a folder, such as a named pipe; hidden files, whose names
    begin with a dot; and files still being downloaded. Stops with OSError where the folder cannot
    be read.
    """
    moves = []
    with os.scandir(folder) as entries:
        for entry in entries:
            if (
                entry.is_file(follow_symlinks=False)
                and not entry.name.startswith(".")
                and not type_table.is_still_downloading(entry.name)
            ):
                moves.append(Move(entry.name, type_table.type_folder_for(entry.name)))
    return sorted(moves)
