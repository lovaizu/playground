"""Run record: the hidden file .organize-last-run inside the organized folder, which holds the moves
of the last run that moved files, so undo can find what to put back.

The record is kept inside the organized folder, so a run changes nothing outside it, and is hidden,
so the planner leaves it in place. It is written as a new file beside it and renamed over it, so a
write cut short, by a full disk or a crash, leaves the last record whole; it is the one file the
tool replaces, being the tool's own and not the user's.
"""

import contextlib
import json
import os
import tempfile
from pathlib import Path

from organize_downloads import organize, type_table

RECORD_NAME = ".organize-last-run"

# The type folders a move in the record may name: those of Type table and Others.
_TYPE_FOLDERS = frozenset(type_table.EXTENSIONS_BY_TYPE_FOLDER) | {type_table.OTHERS}


class RecordNotWritten(OSError):
    """The record could not be written: the error's filename is the record file, its errno and
    strerror those of the write that failed. The record before it is left whole."""


def write_moves(folder: Path, moves: list[organize.Move]) -> None:
    """Take in the organized folder and moves, in the order they were made; write them as the
    folder's record, in place of the one before.

    The moves are written as JSON, a list of {"name": ..., "type_folder": ...}, to a new hidden
    file of this write's own beside the record, so two runs at once never write the same file,
    which is then renamed over the record. Stops with RecordNotWritten where the record cannot be
    written, leaving the record before whole and the new file removed.
    """
    path = folder / RECORD_NAME
    # ensure_ascii writes each character beyond ASCII as an escape, a byte of a name not valid in
    # the system's encoding (held as a surrogate) included, so any name is read back the same.
    text = json.dumps([{"name": move.name, "type_folder": move.type_folder} for move in moves])
    try:
        descriptor, new_file = tempfile.mkstemp(prefix=f"{RECORD_NAME}.", dir=folder)
        try:
            with open(descriptor, "w", encoding="ascii") as file:
                file.write(text)
                file.flush()
                # On the disk before the rename, so a crash after it leaves the new record whole.
                os.fsync(file.fileno())
            os.replace(new_file, path)
        except BaseException:
            # The new file is this write's own and holds nothing of the user's; removing it where
            # it was not put in place, an interrupted write included, leaves no file behind.
            with contextlib.suppress(OSError):
                os.unlink(new_file)
            raise
    except OSError as error:
        raise RecordNotWritten(error.errno, error.strerror, str(path)) from error


def read_moves(folder: Path) -> list[organize.Move]:
    """Take in the organized folder; give back the moves its record holds, in the order written.

    Stops with OSError where the record cannot be read, FileNotFoundError where there is none, and
    with ValueError naming the record where it does not hold moves as write_moves writes them:
    each a file name, not empty, "." or ".." and holding no "/" or NUL, with one of the type
    folders, so a record changed by hand never names a place outside the organized folder.
    """
    path = folder / RECORD_NAME
    try:
        entries = json.loads(path.read_bytes())
    except ValueError as error:
        raise ValueError(f"{path} is not JSON: {error}") from error
    if not isinstance(entries, list) or not all(_is_move(entry) for entry in entries):
        raise ValueError(
            f"{path} does not hold a list of moves, each a file name and its type folder"
        )
    return [organize.Move(entry["name"], entry["type_folder"]) for entry in entries]


def _is_move(entry: object) -> bool:
    """Take in an entry of the record's list; give back whether it is a move write_moves writes:
    an object of a name, a file name directly in a folder, and a type folder."""
    return (
        isinstance(entry, dict)
        and entry.keys() == {"name", "type_folder"}
        and isinstance(entry["name"], str)
        and entry["name"] not in ("", ".", "..")
        and "/" not in entry["name"]
        and "\0" not in entry["name"]
        and isinstance(entry["type_folder"], str)
        and entry["type_folder"] in _TYPE_FOLDERS
    )
