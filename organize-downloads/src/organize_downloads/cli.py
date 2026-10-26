"""Command line: the organize-downloads command, which takes what the user types, finds the folder
to organize, prints the moves the planner works out for it and, with --apply, has Mover make them.

It is the one part that meets the user: it reads the arguments, the home folder and the system's
name, and prints what the run found, what it moved and left, or why it stopped. --help is written
from Type table, so the extensions it shows are always those the planner uses.
"""

import argparse
import os
import platform
import sys
import textwrap
from pathlib import Path

from organize_downloads import folder, mover, organize, record, type_table

PROGRAM = "organize-downloads"

# The width the description and the epilog of --help are wrapped to here: the parser prints them
# as written (RawDescriptionHelpFormatter), so the type table's columns stay lined up.
_HELP_WIDTH = 79


def main(arguments: list[str] | None = None) -> int:
    """Take in the arguments typed after organize-downloads, those of the process where None;
    print where each file in the organized folder would go, moving nothing, or with --apply move
    each and print what was moved and what was left; give back the exit status: 0 where the run
    ended well, a file whose name is taken being left included, 1 where it stopped, after printing
    why on standard error. Exits through argparse, with status 2, on arguments it does not take."""
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
    if not moves:
        print(f"No file to move in {_shown(str(organized))}.")
        return 0
    # One width for every line of the run, so the arrows line up under each heading alike.
    width = max(len(_shown(move.name)) for move in moves)
    if not options.apply:
        print(f"Would move {_count(moves)} in {_shown(str(organized))}:")
        _print_moves(moves, width)
        print("Nothing was moved.")
        return 0
    report = mover.apply_moves(organized, moves)
    _print_report(organized, report, width)
    if report.stopped is None:
        return 0
    return _stop(_why_stopped(organized, report))


def _parser() -> argparse.ArgumentParser:
    """Give back the parser of the command's arguments, its --help written from Type table."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=textwrap.fill(
            "List the type folder each file in your Downloads folder, or in the folder given, "
            "would be moved to. Nothing is moved unless --apply is given.",
            width=_HELP_WIDTH,
        ),
        epilog=_help_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "move each file listed into its type folder, making the folder where it is missing; a "
            "file whose name is already taken there is left where it is"
        ),
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


def _print_report(organized: Path, report: mover.MoveReport, width: int) -> None:
    """Take in the organized folder, what Mover did in it and the width the names are padded to;
    print the files moved, then those left as their names are taken, then those left as the run
    stopped, each group under a heading counting it, and a group with no file left out but the
    first, which says no file moved."""
    if report.moved:
        print(f"Moved {_count(report.moved)} in {_shown(str(organized))}:")
        _print_moves(report.moved, width)
    else:
        print(f"Moved no file in {_shown(str(organized))}.")
    for left, why in [
        (report.name_taken, "as a file of the same name is already in its type folder"),
        (report.unmoved, "as the run stopped"),
    ]:
        if left:
            print(f"Left {_count(left)} in place, {why}:")
            _print_moves(left, width)


def _print_moves(moves: list[organize.Move], width: int) -> None:
    """Take in moves and the width their names are padded to; print each file's name with the
    type folder it goes to, one line each, the names padded so the arrows line up."""
    for move in moves:
        print(f"  {_shown(move.name):<{width}}  -> {move.type_folder}/")


def _count(moves: list[organize.Move]) -> str:
    """Take in moves; give back how many files they are, such as "1 file" or "3 files"."""
    return f"{len(moves)} file" if len(moves) == 1 else f"{len(moves)} files"


def _why_stopped(organized: Path, report: mover.MoveReport) -> str:
    """Take in the organized folder and the report of a run Mover stopped; give back the stop's
    message: what could not be done, the reason, and what the user can do."""
    error = report.stopped
    if isinstance(error, record.RecordNotWritten):
        return (
            f"cannot write {error.filename}, the record undo reads to put files back "
            f"({error.strerror}): check that you may write in {organized} and that its disk has "
            "room, and run again"
        )
    failed = report.unmoved[0]
    cannot = f"cannot move {failed.name} into {failed.type_folder}/"
    if isinstance(error, NotADirectoryError):
        return f"{cannot}, as {error.filename} is not a folder: move or rename it, and run again"
    if isinstance(error, FileNotFoundError):
        return (
            f"{cannot}, as it is no longer in {organized}, such as when another run moves it at "
            "the same time: run again to move the files left"
        )
    return (
        f"{cannot} ({error.strerror}): check that you may write in {organized} and that it is on "
        "a file system that can make hard links, which exFAT and FAT32 cannot"
    )


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
