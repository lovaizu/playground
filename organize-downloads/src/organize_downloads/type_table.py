"""Type table: which type folder a file's name sends it to, and which names are files still being
downloaded.

The table is fixed, as the user cannot change it, and is written here alone, so the planner and
the --help text always use the same extensions.
"""

# Each type folder with the extensions that send a file to it, in lower case, in the order --help
# shows them. A file whose last extension is in none of them goes to OTHERS.
EXTENSIONS_BY_TYPE_FOLDER = {
    "Images": (
        "jpg jpeg png gif webp heic heif bmp tif tiff svg ico psd raw cr2 nef arw dng"
    ).split(),
    "Documents": (
        "pdf doc docx xls xlsx ppt pptx odt ods odp rtf txt md csv tsv pages numbers key epub"
    ).split(),
    "Archives": "zip tar gz tgz bz2 xz zst 7z rar".split(),
    "Audio": "mp3 wav flac aac m4a ogg opus aif aiff wma mid midi".split(),
    "Video": "mp4 mov mkv avi webm m4v wmv flv mpg mpeg 3gp".split(),
    "Installers": "dmg pkg deb rpm appimage flatpak snap iso msi exe".split(),
}
OTHERS = "Others"

# The last extensions of files a browser is still downloading, in lower case: Chrome's,
# Firefox's and Safari's.
DOWNLOADING_ENDINGS = ("crdownload", "part", "download")

_TYPE_FOLDER_BY_EXTENSION = {
    extension: type_folder
    for type_folder, extensions in EXTENSIONS_BY_TYPE_FOLDER.items()
    for extension in extensions
}


def last_extension(name: str) -> str:
    """Take in a file name; give back what follows its last dot, in lower case, so extensions
    match without regard to case; "" for a name with no dot or nothing after its last dot."""
    _, dot, extension = name.rpartition(".")
    return extension.lower() if dot else ""


def type_folder_for(name: str) -> str:
    """Take in a file name; give back the type folder its last extension sends it to, OTHERS
    where that extension is in no folder or the name has none."""
    return _TYPE_FOLDER_BY_EXTENSION.get(last_extension(name), OTHERS)


def is_still_downloading(name: str) -> bool:
    """Take in a file name; give back whether its last extension is one of DOWNLOADING_ENDINGS."""
    return last_extension(name) in DOWNLOADING_ENDINGS
