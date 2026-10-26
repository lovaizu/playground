"""Tests of Folder finder: which folder a run organizes, the one given or else the user's Downloads,
and the stop where there is none to organize.

Each test makes its own home folder in a temporary folder and hands it, with the system's name as
platform.system() gives it, to folder.find_organized_folder, so the macOS and the Linux ways are
both checked on either system and the user's own home is never read.
"""

import os
import random
import tempfile
import unittest
from pathlib import Path

from organize_downloads import folder
from tests import write_user_dirs

# Characters a random folder name is made of, those xdg-user-dirs writes with a backslash before
# them (" \ ` $) included; "/" and NUL, which no folder name holds, and a line break are left out.
FOLDER_NAME_CHARACTERS = 'abcXYZ019 _-.()\'"\\`$#&~äダウンロード文'

# Inputs a property test once failed on, each kept so it is checked on every run.
# Append each failing folder name a property test reports here, as the name it printed.
FAILED_FOLDER_NAMES = []


def shell_escaped(name: str) -> str:
    """Take in a folder name; give back the name as xdg-user-dirs writes it between double quotes,
    a backslash put before each ", \\, ` and $."""
    return "".join("\\" + char if char in '"\\`$' else char for char in name)


class FolderTestCase(unittest.TestCase):
    """A test with its own empty home folder, removed after it."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)

    def assertSameFolder(self, result, expected: Path):
        """Fail unless result is the folder expected, however either path is spelled."""
        self.assertTrue(os.path.samefile(result, expected), f"{result} is not {expected}")


class GivenFolderTest(FolderTestCase):
    """With a folder given, the run organizes that folder, on any system."""

    def test_a_given_folder_is_the_one_organized(self):
        for system in ["Darwin", "Linux"]:
            with self.subTest(system=system):
                # Given: a folder, and a Downloads folder the user-dirs settings also name
                given = self.home / "Desktop"
                given.mkdir(exist_ok=True)
                (self.home / "Downloads").mkdir(exist_ok=True)
                write_user_dirs(self.home, 'XDG_DOWNLOAD_DIR="$HOME/Downloads"\n')
                # When: the folder to organize is found with that folder given
                result = folder.find_organized_folder(str(given), system, self.home)
                # Then: it is the given folder, not Downloads
                self.assertSameFolder(result, given)

    def test_a_given_path_that_does_not_exist_stops_the_run_naming_it(self):
        # Given: a path where there is nothing
        given = self.home / "no-such-folder"
        # When: the folder to organize is found with that path given
        # Then: the run stops, naming the path
        with self.assertRaises(folder.FolderNotFound) as stop:
            folder.find_organized_folder(str(given), "Linux", self.home)
        self.assertIn(str(given), str(stop.exception))

    def test_a_given_path_that_is_a_file_stops_the_run_naming_it(self):
        # Given: a path that is a plain file, not a folder
        given = self.home / "notes.txt"
        given.write_text("notes", encoding="utf-8")
        # When: the folder to organize is found with that path given
        # Then: the run stops, naming the path
        with self.assertRaises(folder.FolderNotFound) as stop:
            folder.find_organized_folder(str(given), "Darwin", self.home)
        self.assertIn(str(given), str(stop.exception))


class MacOSDownloadsTest(FolderTestCase):
    """On macOS with no folder given, the run organizes ~/Downloads."""

    def test_with_no_folder_given_macos_organizes_downloads_in_home(self):
        # Given: a home folder on macOS holding Downloads, and user-dirs settings naming another
        # folder, which macOS does not use
        (self.home / "Downloads").mkdir()
        (self.home / "Other").mkdir()
        write_user_dirs(self.home, 'XDG_DOWNLOAD_DIR="$HOME/Other"\n')
        # When: the folder to organize is found with none given
        result = folder.find_organized_folder(None, "Darwin", self.home)
        # Then: it is ~/Downloads
        self.assertSameFolder(result, self.home / "Downloads")

    def test_with_no_folder_given_and_no_downloads_macos_stops_naming_it(self):
        # Given: a home folder on macOS with no Downloads in it
        # When: the folder to organize is found with none given
        # Then: the run stops, naming ~/Downloads as the folder it did not find
        with self.assertRaises(folder.FolderNotFound) as stop:
            folder.find_organized_folder(None, "Darwin", self.home)
        self.assertIn(str(self.home / "Downloads"), str(stop.exception))

    def test_with_no_folder_given_and_downloads_a_file_macos_stops_naming_it(self):
        # Given: a home folder on macOS where Downloads is a plain file, not a folder
        (self.home / "Downloads").write_text("not a folder", encoding="utf-8")
        # When: the folder to organize is found with none given
        # Then: the run stops, naming ~/Downloads
        with self.assertRaises(folder.FolderNotFound) as stop:
            folder.find_organized_folder(None, "Darwin", self.home)
        self.assertIn(str(self.home / "Downloads"), str(stop.exception))


class LinuxDownloadsTest(FolderTestCase):
    """On Linux with no folder given, the run organizes the download folder xdg-user-dirs'
    settings file (~/.config/user-dirs.dirs) names, and stops where it names none."""

    def test_the_folder_named_under_home_is_organized(self):
        # Given: a home folder on Linux holding Downloads and ダウンロード, and user-dirs
        # settings naming ダウンロード under $HOME
        (self.home / "Downloads").mkdir()
        (self.home / "ダウンロード").mkdir()
        write_user_dirs(self.home, 'XDG_DOWNLOAD_DIR="$HOME/ダウンロード"\n')
        # When: the folder to organize is found with none given
        result = folder.find_organized_folder(None, "Linux", self.home)
        # Then: it is ~/ダウンロード, not ~/Downloads
        self.assertSameFolder(result, self.home / "ダウンロード")

    def test_a_folder_named_by_its_full_path_is_organized(self):
        # Given: user-dirs settings naming the download folder by its full path, outside home
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        write_user_dirs(self.home, f'XDG_DOWNLOAD_DIR="{outside.name}"\n')
        # When: the folder to organize is found with none given
        result = folder.find_organized_folder(None, "Linux", self.home)
        # Then: it is that folder
        self.assertSameFolder(result, Path(outside.name))

    def test_only_the_download_line_of_the_settings_is_read(self):
        # Given: user-dirs settings as xdg-user-dirs writes them, a comment and the other
        # folders' lines around the download folder's
        (self.home / "Téléchargements").mkdir()
        write_user_dirs(
            self.home,
            "# This file is written by xdg-user-dirs-update\n"
            '# XDG_DOWNLOAD_DIR="$HOME/Commented"\n'
            'XDG_DESKTOP_DIR="$HOME/Bureau"\n'
            'XDG_DOWNLOAD_DIR="$HOME/Téléchargements"\n'
            'XDG_MUSIC_DIR="$HOME/Musique"\n',
        )
        # When: the folder to organize is found with none given
        result = folder.find_organized_folder(None, "Linux", self.home)
        # Then: it is the folder on the XDG_DOWNLOAD_DIR line
        self.assertSameFolder(result, self.home / "Téléchargements")

    def test_any_folder_name_written_by_xdg_user_dirs_is_read_back(self):
        # Property: for many random folder names, made anew on each run, written under $HOME as
        # xdg-user-dirs writes them, a backslash before each " \ ` and $, the folder found is
        # the folder of that name.
        rng = random.Random()
        names = FAILED_FOLDER_NAMES + [
            "".join(rng.choice(FOLDER_NAME_CHARACTERS) for _ in range(rng.randint(1, 16)))
            for _ in range(200)
        ]
        for name in names:
            if name in (".", ".."):
                continue
            with self.subTest(name=name):
                # Given: a folder of a random name, named in the user-dirs settings
                (self.home / name).mkdir(exist_ok=True)
                write_user_dirs(self.home, f'XDG_DOWNLOAD_DIR="$HOME/{shell_escaped(name)}"\n')
                # When: the folder to organize is found with none given
                result = folder.find_organized_folder(None, "Linux", self.home)
                # Then: it is the folder of that name
                self.assertSameFolder(result, self.home / name)

    def test_with_no_settings_file_the_run_stops_naming_it(self):
        # Given: a home folder on Linux holding Downloads but no user-dirs settings file
        (self.home / "Downloads").mkdir()
        # When: the folder to organize is found with none given
        # Then: the run stops, naming the settings file, rather than guessing ~/Downloads
        with self.assertRaises(folder.FolderNotFound) as stop:
            folder.find_organized_folder(None, "Linux", self.home)
        self.assertIn(str(self.home / ".config" / "user-dirs.dirs"), str(stop.exception))

    def test_settings_naming_no_download_folder_stop_the_run_naming_them(self):
        for text in [
            "",
            'XDG_DESKTOP_DIR="$HOME/Desktop"\n',
            '# XDG_DOWNLOAD_DIR="$HOME/Downloads"\n',
            # xdg-user-dirs supports only "$HOME/..." and "/..." between double quotes, so a line
            # in another form names no folder.
            "XDG_DOWNLOAD_DIR=Downloads\n",
            'XDG_DOWNLOAD_DIR="Downloads"\n',
        ]:
            with self.subTest(settings=text):
                # Given: a home folder on Linux holding Downloads, and user-dirs settings with no
                # line naming a download folder in a form xdg-user-dirs supports
                (self.home / "Downloads").mkdir(exist_ok=True)
                settings = write_user_dirs(self.home, text)
                # When: the folder to organize is found with none given
                # Then: the run stops, naming the settings file
                with self.assertRaises(folder.FolderNotFound) as stop:
                    folder.find_organized_folder(None, "Linux", self.home)
                self.assertIn(str(settings), str(stop.exception))

    def test_settings_naming_home_itself_stop_the_run_naming_them(self):
        for value in ["$HOME", "$HOME/"]:
            with self.subTest(value=value):
                # Given: user-dirs settings naming the home folder itself as the download folder,
                # as xdg-user-dirs does where the folder was removed
                settings = write_user_dirs(self.home, f'XDG_DOWNLOAD_DIR="{value}"\n')
                # When: the folder to organize is found with none given
                # Then: the run stops, naming the settings file, so home is never organized
                with self.assertRaises(folder.FolderNotFound) as stop:
                    folder.find_organized_folder(None, "Linux", self.home)
                self.assertIn(str(settings), str(stop.exception))

    def test_a_named_folder_that_does_not_exist_stops_the_run_naming_it(self):
        # Given: user-dirs settings naming a download folder that is not there
        write_user_dirs(self.home, 'XDG_DOWNLOAD_DIR="$HOME/Gone"\n')
        # When: the folder to organize is found with none given
        # Then: the run stops, naming the folder it did not find
        with self.assertRaises(folder.FolderNotFound) as stop:
            folder.find_organized_folder(None, "Linux", self.home)
        self.assertIn(str(self.home / "Gone"), str(stop.exception))

    def test_a_named_folder_that_is_a_file_stops_the_run_naming_it(self):
        # Given: user-dirs settings naming a download folder that is a plain file
        (self.home / "Dl").write_text("not a folder", encoding="utf-8")
        write_user_dirs(self.home, 'XDG_DOWNLOAD_DIR="$HOME/Dl"\n')
        # When: the folder to organize is found with none given
        # Then: the run stops, naming the path it found no folder at
        with self.assertRaises(folder.FolderNotFound) as stop:
            folder.find_organized_folder(None, "Linux", self.home)
        self.assertIn(str(self.home / "Dl"), str(stop.exception))
