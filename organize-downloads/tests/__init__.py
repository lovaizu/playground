"""Tests of organize-downloads, and what more than one test module uses: the type folders, endings
and record file name the requirements settle, written here once so no test takes them from the code
it checks, and the helpers that make and read temporary folders.

unittest discover finds the tests either as this package, `tests` (run from the repository with
`-s organize-downloads/tests -t organize-downloads`), or as top-level modules (run in
organize-downloads with `-s tests`, as the GitHub Actions workflow does). Either way the
organize-downloads folder is on sys.path, so every test module imports these helpers with
`from tests import ...`.
"""

import contextlib
import errno
import os
import pathlib
import re
import stat
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from unittest import mock

# AC3: each type folder and the extensions that send a file to it.
EXTENSIONS_BY_FOLDER = {
    "Images": "jpg jpeg png gif webp heic heif bmp tif tiff svg ico psd raw cr2 nef arw dng",
    "Documents": "pdf doc docx xls xlsx ppt pptx odt ods odp rtf txt md csv tsv pages numbers key epub",
    "Archives": "zip tar gz tgz bz2 xz zst 7z rar",
    "Audio": "mp3 wav flac aac m4a ogg opus aif aiff wma mid midi",
    "Video": "mp4 mov mkv avi webm m4v wmv flv mpg mpeg 3gp",
    "Installers": "dmg pkg deb rpm appimage flatpak snap iso msi exe",
}
FOLDER_BY_EXTENSION = {
    extension: folder
    for folder, extensions in EXTENSIONS_BY_FOLDER.items()
    for extension in extensions.split()
}

# AC5: the endings of files still being downloaded (Chrome, Firefox, Safari), matched without
# regard to case.
DOWNLOADING_ENDINGS = ["crdownload", "part", "download"]

# AC8: the hidden file inside the organized folder that holds the moves of the last run that moved
# files.
RECORD_NAME = ".organize-last-run"


def last_extension(name: str) -> str:
    """Take in a file name; give back what follows its last dot, in lower case, or "" for a name
    with no dot."""
    return name.rsplit(".", 1)[1].lower() if "." in name else ""


def expected_type_folder(name: str) -> str:
    """Take in a file name; give back the type folder AC3 sends it to, Others where its last
    extension is in no folder."""
    return FOLDER_BY_EXTENSION.get(last_extension(name), "Others")


# The error a file system that cannot make hard links, such as exFAT or FAT32, gives every link.
# Such a file system cannot be made without being root, so the tests that need one stand in for
# os.link with one that fails so.
NO_HARD_LINKS = OSError(errno.EPERM, os.strerror(errno.EPERM))

# The error of a link that fails for a reason other than its name being taken or the file system,
# such as a disk that fails to write.
WRITE_FAILED = OSError(errno.EIO, os.strerror(errno.EIO))


@contextlib.contextmanager
def stand_in_for_os(**stand_ins: Callable[..., object]) -> Iterator[None]:
    """Take in names of os functions, such as link or replace, each with a stand-in; while the
    context is open, the stand-in is called wherever the code under test calls that function,
    whether it calls os.<name> or a Path method that makes the same call, such as
    Path.hardlink_to or Path.replace.

    On Python 3.10 Path's methods call their own copies of the os functions, kept in
    pathlib._NormalAccessor, which a patch of os does not reach, so those copies are replaced too;
    from 3.11 on Path's methods call os.<name> itself. The code is then free to use either, and a
    test fails on the same faults on every Python the tool keeps to.
    """
    with contextlib.ExitStack() as patches:
        patches.enter_context(mock.patch.multiple(os, **stand_ins))
        accessor = getattr(pathlib, "_NormalAccessor", None)
        if accessor is not None:
            patches.enter_context(
                mock.patch.multiple(
                    accessor,
                    **{name: staticmethod(stand_in) for name, stand_in in stand_ins.items()},
                )
            )
        yield


def link_failing_on_second_call(error: BaseException) -> Callable[..., None]:
    """Take in an error; give back a stand-in for os.link that links as os.link does on every
    call but the second, which raises the error instead, as a run that fails after its first move
    meets."""
    real_link = os.link
    calls = []

    def link(*arguments, **keywords) -> None:
        calls.append(arguments)
        if len(calls) == 2:
            raise error
        real_link(*arguments, **keywords)

    return link


def link_failing_for_name(name: str, error: BaseException) -> Callable[..., None]:
    """Take in a file name and an error; give back a stand-in for os.link that links as os.link
    does, but raises the error instead where the new name it is to make ends in that file name."""
    real_link = os.link

    def link(
        source: os.PathLike | str, destination: os.PathLike | str, *arguments, **keywords
    ) -> None:
        if Path(destination).name == name:
            raise error
        real_link(source, destination, *arguments, **keywords)

    return link


def write_user_dirs(home: Path, text: str) -> Path:
    """Take in a home folder and a text; write the text as xdg-user-dirs' settings file,
    ~/.config/user-dirs.dirs, there and give back the file's path. Stops with OSError if it
    cannot be written."""
    settings = home / ".config" / "user-dirs.dirs"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(text, encoding="utf-8")
    return settings


def make_home(home: Path) -> Path:
    """Take in an empty folder; make it a home whose Downloads folder is named both the macOS way,
    ~/Downloads, and the Linux way, in xdg-user-dirs' settings, and give back that Downloads, so a
    run with no folder given finds it on either system. Stops with OSError if it cannot be made."""
    downloads = home / "Downloads"
    downloads.mkdir()
    write_user_dirs(home, 'XDG_DOWNLOAD_DIR="$HOME/Downloads"\n')
    return downloads


def snapshot(root: Path) -> dict:
    """Take in a folder; give back every entry under it, its subfolders' entries included.

    The result maps each entry's path relative to root to what a run could change in it: its kind
    and, for a plain file, its content and modified time, for a symbolic link, the path it points
    to. Symbolic links are not followed, and a named pipe is not opened, so taking a snapshot
    changes nothing and never waits. Two snapshots are equal only if nothing was added, moved,
    removed or written in between. Stops with OSError if root cannot be read.
    """
    entries = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            path = Path(dirpath, name)
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                entries[str(path.relative_to(root))] = ("link", os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                entries[str(path.relative_to(root))] = ("folder",)
            elif stat.S_ISREG(info.st_mode):
                entries[str(path.relative_to(root))] = (
                    "file",
                    path.read_bytes(),
                    info.st_mtime_ns,
                )
            else:
                entries[str(path.relative_to(root))] = ("other", stat.S_IFMT(info.st_mode))
    return entries


def snapshot_without_record(root: Path, folder: str = "") -> dict:
    """Take in a folder and the organized folder's path relative to it, "" where it is that folder
    itself; give back the folder's snapshot with the record file left out, as a run that moves
    files writes one whose content is Run record's to set. Stops with OSError if root cannot be
    read."""
    entries = snapshot(root)
    entries.pop(os.path.join(folder, RECORD_NAME), None)
    return entries


def after_moves(before: dict, folder: str, moves: Iterable[tuple[str, str]]) -> dict:
    """Take in a snapshot, the organized folder's path relative to its root, "" where it is the
    root itself, and (file name, type folder) pairs; give back the snapshot expected once each file
    is moved into its type folder inside the organized folder.

    Each file's entry goes under its type folder with the same name, content and modified time, and
    each type folder missing is added; nothing else changes.
    """
    after = dict(before)
    for name, type_folder in moves:
        entry = after.pop(os.path.join(folder, name))
        after.setdefault(os.path.join(folder, type_folder), ("folder",))
        after[os.path.join(folder, type_folder, name)] = entry
    return after


def move_pairs(moves: Iterable) -> list[tuple[str, str]]:
    """Take in moves, each with a `name` and a `type_folder`, such as those organize.plan_moves
    gives; give back each as its (name, type_folder) pair, in the same order, so moves compare
    with the pairs a test writes."""
    return [(move.name, move.type_folder) for move in moves]


def make_files(folder: Path, names: Iterable[str]) -> None:
    """Take in a folder and file names; make each name a plain file directly in the folder.

    Each file holds its own name, so files told apart by content are told apart in a snapshot.
    Stops with OSError if a file cannot be made.
    """
    for name in names:
        (folder / name).write_text(name, encoding="utf-8")


# How the heading over the files a run with --apply leaves in place, as their names are taken in
# their type folders, ends after "Left <count> ", such as "Left 1 file ".
NAME_TAKEN_HEADING_END = (
    "in place, as a file of the same name is already in its type folder:"
)

# A line of a run's output that names one file's move, as the README's Example shows it: the file's
# name indented, then "->", then its type folder followed by "/", such as "  holiday.jpg  -> Images/".
_MOVE_LINE = re.compile(r"^\s+(?P<name>.+?)\s+->\s+(?P<type_folder>\S+)/$")


def listed_moves(output: str) -> list:
    """Take in what a run printed; give back each (file name, type folder) its lines name, those
    of files moved and of files left in place alike.

    Lines that name no move, such as a heading, are left out. The list keeps the order printed, so
    a file listed twice shows twice.
    """
    moves = []
    for line in output.splitlines():
        match = _MOVE_LINE.match(line)
        if match:
            moves.append((match["name"], match["type_folder"]))
    return moves
