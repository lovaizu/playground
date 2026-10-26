"""Mover: makes the moves Organize planner works out, putting each file into its type folder inside
the organized folder under the same name, and writes each move made to Run record.

Mover is the one part that changes the organized folder. It gives a file its new name as a hard
link and only then removes the old name, never renaming over a name: the link fails where the name
is already taken, even by a file that came after the moves were worked out, so no file of the
user's is ever overwritten. Where a link fails for another reason, such as on a file system that
cannot make hard links, the run stops there rather than move by a rename that could overwrite.
"""

import contextlib
import errno
import os
import stat
from pathlib import Path
from typing import NamedTuple

from organize_downloads import organize, record


class MoveReport(NamedTuple):
    """What a run of moves did.

    `moved` holds the moves made, in the order made; `name_taken`, the moves left undone because an
    entry of the same name is already in the type folder; `stopped`, the error that stopped the
    run, None where none did; and `unmoved`, the moves the stop left undone: the one that failed
    for that reason, and each one after it, which was not tried.
    """

    moved: list[organize.Move]
    name_taken: list[organize.Move]
    stopped: OSError | None
    unmoved: list[organize.Move]


def apply_moves(folder: Path, moves: list[organize.Move]) -> MoveReport:
    """Take in the organized folder and the moves planned for it; make each move in order and give
    back what was done.

    Each file goes into its type folder, made where nothing has its name, and each move made is
    written to the folder's Run record at once, in place of the run before's, so a run stopped or
    interrupted midway still leaves undo what it moved; a run that moves nothing leaves the record
    as it was. The run stops, with the error in the report, at the first move that fails for a
    reason other than the name being taken: a type folder's name held by something not a folder
    (NotADirectoryError), a link or a removal that fails, or a record that cannot be written
    (record.RecordNotWritten), a file no longer there, such as one another run at the same time
    moved, among them (FileNotFoundError). The move that stops it is undone where it was begun, so
    its file keeps its old name, but for a file that cannot be given its old name back after the
    record failed, which stays moved and is reported so; nothing is deleted, and a type folder made
    stays.
    """
    moved: list[organize.Move] = []
    name_taken: list[organize.Move] = []
    for index, move in enumerate(moves):
        source = folder / move.name
        try:
            target = _type_folder(folder, move.type_folder) / move.name
            os.link(source, target)
        except FileExistsError:
            name_taken.append(move)
            continue
        except OSError as error:
            return MoveReport(moved, name_taken, error, moves[index:])
        try:
            os.unlink(source)
        except OSError as error:
            # The file keeps its old name alone, as it was.
            _remove_name(target)
            return MoveReport(moved, name_taken, error, moves[index:])
        try:
            record.write_moves(folder, moved + [move])
        except record.RecordNotWritten as error:
            # A move undo cannot find is put back. Where that fails, as when a file of the same
            # name came to the old place meanwhile, the file stays moved, and is told as moved.
            if _put_back(source, target):
                return MoveReport(moved, name_taken, error, moves[index:])
            return MoveReport(moved + [move], name_taken, error, moves[index + 1 :])
        moved.append(move)
    return MoveReport(moved, name_taken, None, [])


def _type_folder(folder: Path, name: str) -> Path:
    """Take in the organized folder and a type folder's name; give back the type folder's path,
    making the folder where nothing has that name.

    Stops with NotADirectoryError naming the path where something not a folder holds the name, a
    symbolic link to a folder included, as moving through it would write outside the organized
    folder; and with OSError where the folder cannot be made.
    """
    path = folder / name
    try:
        os.mkdir(path)
    except FileExistsError:
        if not stat.S_ISDIR(os.lstat(path).st_mode):
            raise NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), str(path)) from None
    return path


def _put_back(source: Path, target: Path) -> bool:
    """Take in a moved file's old path and its path in the type folder; give it back its old name,
    overwriting nothing, and give back whether it was put back."""
    try:
        os.link(target, source)
    except OSError:
        return False
    _remove_name(target)
    return True


def _remove_name(path: Path) -> None:
    """Take in the name in a type folder a move has just given a file, which still has its old name
    too; remove that new name. Where it cannot be removed, the file keeps both names, and nothing
    of it is lost."""
    with contextlib.suppress(OSError):
        os.unlink(path)
