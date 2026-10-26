"""Tests of organize-downloads, and what more than one test module uses: the type folders and
endings the requirements settle, written here once so no test takes them from the code it checks,
and the helpers that make and read temporary folders.

unittest discover finds the tests either as this package, `tests` (run from the repository with
`-s organize-downloads/tests -t organize-downloads`), or as top-level modules (run in
organize-downloads with `-s tests`, as the GitHub Actions workflow does). Either way the
organize-downloads folder is on sys.path, so every test module imports these helpers with
`from tests import ...`.
"""

import os
import re
import stat
from pathlib import Path

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


def last_extension(name: str) -> str:
    """Take in a file name; give back what follows its last dot, in lower case, or "" for a name
    with no dot."""
    return name.rsplit(".", 1)[1].lower() if "." in name else ""


def expected_type_folder(name: str) -> str:
    """Take in a file name; give back the type folder AC3 sends it to, Others where its last
    extension is in no folder."""
    return FOLDER_BY_EXTENSION.get(last_extension(name), "Others")


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


def make_files(folder: Path, names) -> None:
    """Take in a folder and file names; make each name a plain file directly in the folder.

    Each file holds its own name, so files told apart by content are told apart in a snapshot.
    Stops with OSError if a file cannot be made.
    """
    for name in names:
        (folder / name).write_text(name, encoding="utf-8")


# A line of the listing that names one file's move, as the README's Example shows it: the file's
# name indented, then "->", then its type folder followed by "/", such as "  holiday.jpg  -> Images/".
_MOVE_LINE = re.compile(r"^\s+(?P<name>.+?)\s+->\s+(?P<type_folder>\S+)/$")


def listed_moves(output: str) -> list:
    """Take in what a run printed; give back each (file name, type folder) its listing names.

    Lines that name no move, such as a heading, are left out. The list keeps the order printed, so
    a file listed twice shows twice.
    """
    moves = []
    for line in output.splitlines():
        match = _MOVE_LINE.match(line)
        if match:
            moves.append((match["name"], match["type_folder"]))
    return moves
