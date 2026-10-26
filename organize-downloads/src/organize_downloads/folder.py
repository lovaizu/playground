"""Folder finder: which folder a run organizes, the one the user gives or else their Downloads
folder, and the stop where there is none to organize.

On Linux the Downloads folder is the one xdg-user-dirs, the freedesktop.org tool that names the
user's folders, writes in its settings file; this module reads that file itself rather than run
the xdg-user-dir command, so the tool runs no other program. It only reads, and changes nothing.
"""

import os
import re
from pathlib import Path

# A line of xdg-user-dirs' settings naming the download folder, as xdg-user-dirs writes it and
# reads it back: XDG_DOWNLOAD_DIR="<value>", spaces allowed around "=", the value between double
# quotes with a backslash before each character that follows it as is, such as \" or \$. A line
# in another form, a comment ("#...") among them, names no folder.
_DOWNLOAD_LINE = re.compile(r'\s*XDG_DOWNLOAD_DIR\s*=\s*"(?P<value>(?:[^"\\]|\\.)*)"')
_ESCAPED_CHARACTER = re.compile(r"\\(.)")


class FolderNotFound(Exception):
    """The run has no folder to organize; the message names the path or settings file that was
    wrong and the condition. What the user can do instead, give a folder last, is for the command
    line to add, as it names the command."""


def find_organized_folder(given: str | None, system: str, home: Path) -> Path:
    """Take in the folder the user gave, None where none was given, the system's name as
    platform.system() gives it, and the user's home folder; give back the folder to organize.

    A given folder is organized on any system. With none given, it is ~/Downloads on macOS
    ("Darwin"), and on any other system, Linux among them, the download folder xdg-user-dirs'
    settings file, ~/.config/user-dirs.dirs, names. Stops with FolderNotFound where the given
    path, or the folder found, is not a folder, and on Linux where the settings file cannot be
    read, names no download folder, or names the home folder itself, so home is never organized.
    """
    if given is not None:
        return _existing_folder(Path(given), "")
    if system == "Darwin":
        return _existing_folder(home / "Downloads", "the Downloads folder ")
    settings = home / ".config" / "user-dirs.dirs"
    downloads = _download_folder_named_in(settings, home)
    return _existing_folder(downloads, f"the download folder {settings} names, ")


def _existing_folder(path: Path, what: str) -> Path:
    """Take in a path and what it is, such as "the Downloads folder ", told before it in a stop;
    give back the path where it is a folder. Stops with FolderNotFound naming it otherwise."""
    if not path.is_dir():
        reason = "does not exist" if not os.path.lexists(path) else "is not a folder"
        raise FolderNotFound(f"{what}{path} {reason}")
    return path


def _download_folder_named_in(settings: Path, home: Path) -> Path:
    """Take in the path of xdg-user-dirs' settings file and the home folder; give back the
    download folder the file names, its last XDG_DOWNLOAD_DIR line read as xdg-user-dirs reads
    it: "$HOME" at the start stands for the home folder, and a value is otherwise a full path.
    Stops with FolderNotFound naming the file where it cannot be read, names no download folder
    in either form, or names the home folder itself."""
    try:
        # Read as bytes and decoded as the system decodes file names, so a folder name in any
        # bytes comes back as the same name.
        text = os.fsdecode(settings.read_bytes())
    except OSError as error:
        raise FolderNotFound(
            f"cannot read {settings}, where xdg-user-dirs names the download folder "
            f"({error.strerror})"
        ) from error
    downloads = None
    for line in text.splitlines():
        match = _DOWNLOAD_LINE.match(line)
        if not match:
            continue
        value = _ESCAPED_CHARACTER.sub(r"\1", match["value"])
        if value == "$HOME" or value.startswith("$HOME/"):
            downloads = Path(str(home) + value[len("$HOME"):])
        elif value.startswith("/"):
            downloads = Path(value)
    if downloads is None:
        raise FolderNotFound(
            f'{settings} names no download folder, in a line XDG_DOWNLOAD_DIR="$HOME/<folder>"'
        )
    if os.path.normpath(downloads) == os.path.normpath(home):
        raise FolderNotFound(
            f"{settings} names your home folder itself as the download folder, which the tool "
            "does not organize"
        )
    return downloads
