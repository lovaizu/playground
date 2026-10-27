#!/usr/bin/env python3
"""sort-downloads: sorts the files lying loose in a folder into folders by kind.

Run with no folder, it works on ~/Downloads. For each file directly in the folder it
shows the folder of its kind, such as Images or Documents, it would move to, and each
file it would leave there, with the reason; with --move it moves them, making each kind
folder that is not there, and keeps a record of the sort. What it prints is the README's
Example, and how the program is put together is docs/architecture.md: this file holds
the Command line (main), the Sort planner (plan_sort), the Mover (move_files), the Last
sort record (last_sort_record, write_record) and the Report (print_preview,
print_sorted).

It needs only Python 3.9 or newer and its standard library, as that is all the README
asks the user to have.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

# Each kind folder, with the endings of the files that go to it, in the README's table's
# order; a unit test keeps the two the same.
KINDS: dict[str, tuple[str, ...]] = {
    "Images": (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".heic",
        ".webp",
        ".svg",
        ".bmp",
        ".tif",
        ".tiff",
    ),
    "Documents": (
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".odt",
        ".ods",
        ".odp",
        ".pages",
        ".numbers",
        ".key",
        ".txt",
        ".md",
        ".rtf",
        ".csv",
        ".epub",
    ),
    "Videos": (".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".wmv"),
    "Music": (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".aiff"),
    "Archives": (".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar", ".dmg"),
}

# The folder of a file whose ending, or lack of one, no kind lists.
OTHERS = "Others"

# Each ending's kind folder, read from KINDS.
KIND_OF_ENDING = {ending: kind for kind, endings in KINDS.items() for ending in endings}

# Endings a browser gives a file it is still downloading: Chrome's and Firefox's.
DOWNLOADING_ENDINGS = (".crdownload", ".part")

# The reasons a file is left, as the Report prints them.
HIDDEN = "hidden file"
DOWNLOADING = "download still running"


@dataclass(frozen=True)
class Move:
    """A file's move into the folder of its kind, keeping its name.

    Attributes:
        name: The file's name, directly in the sorted folder.
        kind: The kind folder, inside the sorted folder, it moves to.
    """

    name: str
    kind: str


@dataclass(frozen=True)
class Leave:
    """A file left where it is.

    Attributes:
        name: The file's name, directly in the sorted folder.
        reason: Why it is left, as the Report prints it.
    """

    name: str
    reason: str


@dataclass(frozen=True)
class SortDone:
    """What a sort of one folder did.

    Attributes:
        folder: The folder sorted.
        moved: The files moved, by name.
        left: The files left: those the Mover found the place taken for, or could not
            move, by name, then those the plan left, in the plan's order.
    """

    folder: Path
    moved: list[Move]
    left: list[Leave]


@dataclass(frozen=True)
class SortPlan:
    """What a sort of one folder would do.

    Attributes:
        folder: The folder sorted.
        moves: The files to move, by name.
        leaves: The files to leave, those whose name is taken first, then hidden ones,
            then downloads still running, as the README lists the reasons; by name
            within each.
    """

    folder: Path
    moves: list[Move]
    leaves: list[Leave]


def by_name(names: list[str]) -> list[str]:
    """Order file names as a person reads a list of them.

    Args:
        names: The names.

    Returns:
        The names with capital letters counted as small ones, and names alike but for
        their capitals in a fixed order, so every run lists them the same.
    """
    return sorted(names, key=lambda name: (name.casefold(), name))


def needed_place(folder: Path, kind: str, name: str) -> Path:
    """Give the place a file's move into its kind folder needs free.

    Where the kind folder is there, the move needs the file's name in it; where it is
    not, the move needs the kind folder's own name, as the Mover makes the folder there.
    So a file named Images takes the place every photo needs.

    Args:
        folder: The folder sorted.
        kind: The kind folder the file would move to.
        name: The file's name.

    Returns:
        The place, inside the folder.
    """
    kind_folder = folder / kind
    return kind_folder / name if os.path.isdir(kind_folder) else kind_folder


def name_taken(folder: Path, name: str, place: Path) -> Leave:
    """Leave a file whose move needs a place something else takes.

    Args:
        folder: The folder sorted.
        name: The file's name.
        place: The place taken, as needed_place() gives it.

    Returns:
        The file left, with the place taken as its reason.
    """
    return Leave(name, f"{place.relative_to(folder)} already exists")


def plan_sort(folder: Path) -> SortPlan:
    """Plan the sort of the files directly in a folder.

    A file is left where it is when its name starts with "." (hidden), when its
    last ending is one a browser gives a download still running, or when the place
    its move needs is taken; any other file would move to the folder of its last
    ending, capitals counted as small letters, or to Others. Folders, and what is in
    them, are not looked into.
    Nothing is changed.

    Args:
        folder: A folder that exists and can be read.

    Returns:
        The plan for the folder.
    """
    with os.scandir(folder) as entries:
        # is_file() follows a symbolic link, so a link to a folder is left out as a
        # folder is.
        names = by_name([entry.name for entry in entries if entry.is_file()])
    moves: list[Move] = []
    taken: list[Leave] = []
    hidden: list[Leave] = []
    downloading: list[Leave] = []
    for name in names:
        if name.startswith("."):
            hidden.append(Leave(name, HIDDEN))
            continue
        ending = os.path.splitext(name)[1].lower()
        if ending in DOWNLOADING_ENDINGS:
            downloading.append(Leave(name, DOWNLOADING))
            continue
        kind = KIND_OF_ENDING.get(ending, OTHERS)
        place = needed_place(folder, kind, name)
        # lexists: a symbolic link there, even one to nothing, takes the place too.
        if os.path.lexists(place):
            taken.append(name_taken(folder, name, place))
        else:
            moves.append(Move(name, kind))
    return SortPlan(folder, moves, taken + hidden + downloading)


def last_sort_record() -> Path:
    """Give the path of the Last sort record, as docs/architecture.md places it.

    Returns:
        last-sort.json in the sort-downloads folder of $XDG_STATE_HOME, or of
        ~/.local/state where it is not set; a path in it that is not absolute is not
        used either, as the XDG Base Directory Specification says.
    """
    state = os.environ.get("XDG_STATE_HOME", "")
    base = Path(state) if os.path.isabs(state) else Path.home() / ".local" / "state"
    return base / "sort-downloads" / "last-sort.json"


def write_record(
    record: Path, folder: Path, made: list[str], moved: list[Move]
) -> None:
    """Put a new Last sort record in the place of the old one.

    It is written to a new file beside the record, named for this write alone, then
    put in the record's place, so the record is never left half written and two runs
    at once never write into one file; the record is the last one put in place.

    Args:
        record: The record's path, as last_sort_record() gives it.
        folder: The folder sorted.
        made: The kind folders the sort made, in the order it made them.
        moved: The files the sort moved, in the order it moved them.
    """
    record.parent.mkdir(parents=True, exist_ok=True)
    handle, written = tempfile.mkstemp(dir=record.parent, prefix=f".{record.name}.")
    with os.fdopen(handle, "w", encoding="utf-8") as file:
        json.dump(
            {
                "folder": str(folder),
                "made": made,
                "moved": [{"name": move.name, "kind": move.kind} for move in moved],
            },
            file,
            indent=2,
        )
    os.replace(written, record)


def move_files(plan: SortPlan, record: Path) -> SortDone:
    """Make the moves of a sort's plan, one at a time, keeping the record of each.

    The record is first replaced with an empty one for the folder, then written again
    as soon as each kind folder is made and each file moved, so a sort cut off part
    way can still be undone for what it did. A file is moved by giving it its new name
    and then taking away its old one, and the new name is given by a step that fails
    where the name is taken, so a file saved there since the plan is never written
    over: the file is then left, with that reason. A file whose kind folder cannot be
    made or written into, or which cannot be given its new name for another reason,
    such as being gone since the plan, is left with the system's reason, and the
    other files still move.

    Args:
        plan: The plan, as plan_sort() gives it.
        record: The record's path, as last_sort_record() gives it.

    Returns:
        What the sort did.

    Raises:
        OSError: Where the record cannot be written, or a file given its new name
            cannot have its old one taken away; what was done before is in the record.
    """
    made: list[str] = []
    moved: list[Move] = []
    left: list[Leave] = []
    write_record(record, plan.folder, made, moved)
    for move in plan.moves:
        kind_folder = plan.folder / move.kind
        old = plan.folder / move.name
        try:
            if not os.path.isdir(kind_folder):
                os.mkdir(kind_folder)
                made.append(move.kind)
                write_record(record, plan.folder, made, moved)
            # follow_symlinks=False: a symbolic link is moved itself, not what it
            # points to.
            os.link(old, kind_folder / move.name, follow_symlinks=False)
        except FileExistsError:
            place = needed_place(plan.folder, move.kind, move.name)
            left.append(name_taken(plan.folder, move.name, place))
            continue
        except OSError as error:
            # strerror: the system's words for the cause, such as "Permission
            # denied", which tell the user what to change, without Python's own.
            reason = f"could not move to {move.kind}/{move.name}: {error.strerror}"
            left.append(Leave(move.name, reason))
            continue
        os.unlink(old)
        moved.append(move)
        write_record(record, plan.folder, made, moved)
    return SortDone(plan.folder, moved, left + plan.leaves)


def print_lists(
    folder: Path,
    moves: list[Move],
    leaves: list[Leave],
    headings: tuple[str, str],
) -> None:
    """Print the folder, then its files moving and its files left, to standard output.

    A heading with nothing under it is not printed.

    Args:
        folder: The folder sorted.
        moves: The files moving, each printed with the place it goes to.
        leaves: The files left, each printed with its reason.
        headings: The heading of the files moving and that of the files left.
    """
    print(f"In {folder}:")
    if moves:
        print(headings[0])
        for move in moves:
            print(f"  {move.name} -> {move.kind}/{move.name}")
    if leaves:
        print(headings[1])
        for leave in leaves:
            print(f"  {leave.name}: {leave.reason}")


def print_preview(plan: SortPlan) -> None:
    """Print a sort's plan as the README's Example shows it, to standard output.

    Args:
        plan: The plan to print.
    """
    print_lists(plan.folder, plan.moves, plan.leaves, ("Would move:", "Would leave:"))
    hint = " Run again with --move to move these files." if plan.moves else ""
    print(f"Nothing was moved.{hint}")


def print_sorted(done: SortDone) -> None:
    """Print what a sort did as the README's Example of --move shows it.

    Args:
        done: What the sort did.
    """
    print_lists(done.folder, done.moved, done.left, ("Moved:", "Left:"))


class Parser(argparse.ArgumentParser):
    """The command's argument parser, whose every stop says where to see the options."""

    def error(self, message: str) -> NoReturn:
        """Stop with the usage, what was wrong, and how to see every option.

        Args:
            message: What was wrong.

        Raises:
            SystemExit: Always, with status 2, as argparse stops.
        """
        self.print_usage(sys.stderr)
        self.exit(
            2,
            f"{self.prog}: {message}\n"
            f"Run '{self.prog} --help' to see every option it takes.\n",
        )


def main(argv: list[str]) -> int:
    """Run the command: check what it is given, plan the sort, and act on the plan.

    Without --move it prints the plan; with --move it makes the plan and prints what
    it did.

    Args:
        argv: The arguments after the command's name.

    Returns:
        0, the run's exit status.

    Raises:
        SystemExit: With status 0 after printing the help, or with status 2 on an
            option it does not take, more than one folder, or a folder named, or
            ~/Downloads where none is, that is not a folder it can read, or with
            --move one it can read and change.
        OSError: As move_files() raises it.
    """
    parser = Parser(
        prog="sort-downloads",
        description=(
            "Show which folder of its kind, such as Images or Documents, each file "
            "lying directly in a folder would move to, and which files would be left "
            "and why. Nothing is moved unless --move is given."
        ),
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="move the files as shown, making each kind folder that is not there",
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="the folder to sort (default: ~/Downloads)",
    )
    arguments = parser.parse_args(argv)
    named = arguments.folder
    folder = Path(os.path.abspath(named)) if named else Path.home() / "Downloads"
    # One check for a path that is missing, is not a folder, cannot be listed, or with
    # --move cannot be changed, as the user does the same for each: name another folder.
    # It comes before the Mover replaces the record, so the last sort's record is kept.
    access, can, command = os.R_OK | os.X_OK, "read", "sort-downloads"
    if arguments.move:
        access, can, command = access | os.W_OK, "read and changed", f"{command} --move"
    if not (folder.is_dir() and os.access(folder, access)):
        parser.error(
            f"{folder} is not a folder that can be {can}; name one that is after the "
            f"command, such as: {command} ~/Desktop"
        )
    plan = plan_sort(folder)
    if arguments.move:
        print_sorted(move_files(plan, last_sort_record()))
    else:
        print_preview(plan)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
