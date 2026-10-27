#!/usr/bin/env python3
"""sort-downloads: shows where each file lying loose in a folder would move, by kind.

Run with no folder, it looks at ~/Downloads. For each file directly in the folder it
shows the folder of its kind, such as Images or Documents, it would move to, and each
file it would leave there, with the reason; it moves nothing. What it prints is the
README's Example, and how the program is put together is docs/architecture.md: this
file holds the Command line (main), the Sort planner (plan_sort) and the Report
(print_preview).

It needs only Python 3.9 or newer and its standard library, as that is all the README
asks the user to have.
"""

from __future__ import annotations

import argparse
import os
import sys
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
    """A file the plan would move into the folder of its kind, keeping its name.

    Attributes:
        name: The file's name, directly in the sorted folder.
        kind: The kind folder, inside the sorted folder, it would move to.
    """

    name: str
    kind: str


@dataclass(frozen=True)
class Leave:
    """A file the plan would leave where it is.

    Attributes:
        name: The file's name, directly in the sorted folder.
        reason: Why it is left, as the Report prints it.
    """

    name: str
    reason: str


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


def plan_sort(folder: Path) -> SortPlan:
    """Plan the sort of the files directly in a folder.

    A file is left where it is when its name starts with "." (hidden), when its
    last ending is one a browser gives a download still running, or when its kind
    folder already holds that name; any other file would move to the folder of its
    last ending, capitals counted as small letters, or to Others. Folders, and what
    is in them, are not looked into.
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
        # lexists: a symbolic link there, even one to nothing, takes the name too.
        if os.path.lexists(folder / kind / name):
            taken.append(Leave(name, f"{kind}/{name} already exists"))
        else:
            moves.append(Move(name, kind))
    return SortPlan(folder, moves, taken + hidden + downloading)


def print_preview(plan: SortPlan) -> None:
    """Print a sort's plan as the README's Example shows it, to standard output.

    A heading with nothing under it is not printed.

    Args:
        plan: The plan to print.
    """
    print(f"In {plan.folder}:")
    if plan.moves:
        print("Would move:")
        for move in plan.moves:
            print(f"  {move.name} -> {move.kind}/{move.name}")
    if plan.leaves:
        print("Would leave:")
        for leave in plan.leaves:
            print(f"  {leave.name}: {leave.reason}")
    hint = " Run again with --move to move these files." if plan.moves else ""
    print(f"Nothing was moved.{hint}")


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
    """Run the command: check what it is given, plan the sort and print the plan.

    Args:
        argv: The arguments after the command's name.

    Returns:
        0, the run's exit status.

    Raises:
        SystemExit: With status 0 after printing the help, or with status 2 on an
            option it does not take, more than one folder, or a folder named, or
            ~/Downloads where none is, that is not a folder it can read.
    """
    parser = Parser(
        prog="sort-downloads",
        description=(
            "Show which folder of its kind, such as Images or Documents, each file "
            "lying directly in a folder would move to, and which files would be left "
            "and why. Nothing is moved."
        ),
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="the folder to look at (default: ~/Downloads)",
    )
    arguments = parser.parse_args(argv)
    named = arguments.folder
    folder = Path(os.path.abspath(named)) if named else Path.home() / "Downloads"
    # One check for a path that is missing, is not a folder, or cannot be listed, as the
    # user does the same for each: name another folder.
    if not (folder.is_dir() and os.access(folder, os.R_OK | os.X_OK)):
        parser.error(
            f"{folder} is not a folder that can be read; name one that is after the "
            "command, such as: sort-downloads ~/Desktop"
        )
    print_preview(plan_sort(folder))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
