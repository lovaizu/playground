"""Command line: the organize-downloads command, which takes what the user types, finds the folder
to organize and prints the moves the planner works out for it.

It is the one part that meets the user: it reads the arguments, the home folder and the system's
name, and prints what the run found or why it stopped. --help is written from Type table, so the
extensions it shows are always those the planner uses.
"""

import argparse
import os
import platform
import sys
import textwrap
from pathlib import Path

from organize_downloads import folder, organize, type_table

PROGRAM = "organize-downloads"

# The width the description and the epilog of --help are wrapped to here: the parser prints them
# as written (RawDescriptionHelpFormatter), so the type table's columns stay lined up.
_HELP_WIDTH = 79


def main(arguments: list[str] | None = None) -> int:
    """Take in the arguments typed after organize-downloads, those of the process where None;
    print where each file in the organized folder would go, moving nothing, and give back the
    exit status: 0 where the moves were listed, 1 where the run stopped, after printing why on
    standard error. Exits through argparse, with status 2, on arguments it does not take."""
    options = _parser().parse_args(arguments)
    try:
        organized = folder.find_organized_folder(options.folder, platform.system(), Path.home())
    except folder.FolderNotFound as stop:
        return _stop(f"{stop}: give the folder to organize last: {PROGRAM} <folder>")
    try:
        moves = organize.plan_moves(organized)
    except OSError as error:
        return _stop(
            f"cannot read {organized} ({error.strerror}): check that you may read it, or give "
            "another folder last"
        )
    _print_moves(organized, moves)
    return 0


def _parser() -> argparse.ArgumentParser:
    """Give back the parser of the command's arguments, its --help written from Type table."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=textwrap.fill(
            "List the type folder each file in your Downloads folder, or in the folder given, "
            "would be moved to. Nothing is moved.",
            width=_HELP_WIDTH,
        ),
        epilog=_help_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help=(
            "the folder to organize; with none given, ~/Downloads on macOS, and on Linux the "
            "download folder xdg-user-dirs' settings, ~/.config/user-dirs.dirs, name"
        ),
    )
    return parser


def _help_epilog() -> str:
    """Give back the part of --help after the arguments: which extensions go to which type folder,
    and which entries are left in place, from Type table."""
    width = max(len(name) for name in type_table.EXTENSIONS_BY_TYPE_FOLDER) + 2
    table = [
        textwrap.fill(
            " ".join(extensions),
            width=_HELP_WIDTH,
            initial_indent=f"  {type_folder:<{width}}",
            subsequent_indent=" " * (width + 2),
        )
        for type_folder, extensions in type_table.EXTENSIONS_BY_TYPE_FOLDER.items()
    ]
    table.append(f"  {type_table.OTHERS:<{width}}every other file, one with no extension included")
    *others, last = [f".{ending}" for ending in type_table.DOWNLOADING_ENDINGS]
    introduction = textwrap.fill(
        "Each file directly in the folder goes to the type folder of its last extension, matched "
        "without regard to case (report.tar.gz goes by gz):",
        width=_HELP_WIDTH,
    )
    left_in_place = textwrap.fill(
        "Left where they are and not listed: folders and what is inside them, symbolic links, "
        "other entries that are not plain files, hidden files (whose names begin with a dot), "
        f"and files still being downloaded (ending in {', '.join(others)} or {last}, in any case).",
        width=_HELP_WIDTH,
    )
    return introduction + "\n\n" + "\n".join(table) + "\n\n" + left_in_place


def _print_moves(organized: Path, moves: list[organize.Move]) -> None:
    """Take in the organized folder and the moves planned for it; print each file's name with the
    type folder it would go to, the names padded so the arrows line up, and that nothing was
    moved."""
    if not moves:
        print(f"No file to move in {_shown(str(organized))}.")
        return
    count = f"{len(moves)} file" if len(moves) == 1 else f"{len(moves)} files"
    print(f"Would move {count} in {_shown(str(organized))}:")
    names = [_shown(move.name) for move in moves]
    width = max(len(name) for name in names)
    for name, move in zip(names, moves):
        print(f"  {name:<{width}}  -> {move.type_folder}/")
    print("Nothing was moved.")


def _shown(text: str) -> str:
    """Take in a text holding file or folder names; give back the text as it can be printed on one
    line.

    Bytes of a name that are not valid in the system's encoding, which Python holds as
    surrogates and cannot print, are written as \\xNN, and characters that cannot be shown, such
    as a line break, as their escape in a Python string, such as \\n, which ascii() gives between
    quotes; every other character is kept as it is.
    """
    text = os.fsencode(text).decode(sys.getfilesystemencoding(), "backslashreplace")
    return "".join(char if char.isprintable() else ascii(char)[1:-1] for char in text)


def _stop(message: str) -> int:
    """Take in why the run stops and what the user can do; print it on standard error, after the
    command's name, and give back the exit status of a stop, 1."""
    print(f"{PROGRAM}: {_shown(message)}", file=sys.stderr)
    return 1
