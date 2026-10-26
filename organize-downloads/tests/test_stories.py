"""Tests of the user stories of the run with nothing added and the run with --apply, each running
the installed organize-downloads command end to end on a temporary folder, as the user meets it.

The command is the one on PATH, as pipx or uv installed it; each story runs it with HOME set to a
temporary home, so it never reads or changes the user's own home, and checks that home whole
afterwards, as nothing outside the organized folder may change. An install made before the code
was last changed runs the old code, so one test fails, naming the files that differ, unless the
command on PATH runs the code in src as it now is.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import (
    NAME_TAKEN_HEADING_END,
    RECORD_NAME,
    after_moves,
    listed_moves,
    make_files,
    make_home,
    snapshot,
    snapshot_without_record,
    write_user_dirs,
)

COMMAND = "organize-downloads"

# The package the stories must run: the code in src next to this tests folder.
SOURCE = Path(__file__).resolve().parents[1] / "src" / "organize_downloads"

# How to put the code as it now is on PATH, said by each test that finds it is not. uv keeps its
# build of a local folder and builds it again only when pyproject.toml changes, not when src
# does, so the uv way needs --no-cache.
INSTALL_HINT = (
    "install it anew after each change with `pipx install --force ./organize-downloads`, or run "
    "the tests through `uv run --isolated --no-project --no-cache --with ./organize-downloads`, "
    "which builds the code as it is on every run"
)


def installed_package(command: str) -> Path:
    """Take in the path of the installed command; give back the folder of the organize_downloads
    package the command's own Python imports.

    The command is a script in the bin folder of the environment pipx or uv made, beside that
    environment's python, or else naming it on its first line (#!). The python is run isolated
    (-I), so neither PYTHONPATH nor the current folder can make it import src instead. Stops with
    subprocess.CalledProcessError if that Python cannot import the package.
    """
    script = Path(command).resolve()
    python = script.parent / "python"
    if not python.exists():
        python = Path(script.read_text(encoding="utf-8").splitlines()[0][2:].strip())
    found = subprocess.run(
        [str(python), "-I", "-c", "import organize_downloads; print(organize_downloads.__file__)"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return Path(found.stdout.strip()).parent


def python_files(package: Path) -> dict:
    """Take in a package folder; give back each .py file directly in it, by name, with its content."""
    return {path.name: path.read_bytes() for path in package.glob("*.py")}


def run_command(home: Path, arguments: list) -> subprocess.CompletedProcess:
    """Take in a home folder and the arguments typed after organize-downloads; run the installed
    command with HOME set to that home and give back how it ended and what it printed.

    XDG_CONFIG_HOME is left out, so the command finds xdg-user-dirs' settings under the home given.
    Stops with FileNotFoundError if the command is not on PATH.
    """
    environment = dict(os.environ, HOME=str(home))
    environment.pop("XDG_CONFIG_HOME", None)
    return subprocess.run(
        [COMMAND, *arguments],
        cwd=home,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


class StoryTestCase(unittest.TestCase):
    """A story with its own temporary home holding a Downloads folder, named the macOS way and in
    xdg-user-dirs' settings the Linux way, so the story holds on either system."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.downloads = make_home(self.home)


class InstallStoryTest(unittest.TestCase):
    """As the user, I want to install the tool from GitHub with pipx or uv, so that the
    organize-downloads command is on my PATH."""

    def test_the_installed_command_is_on_path(self):
        # Given: the tool installed with pipx or uv, as the README says
        # When: the command is looked for on PATH
        found = shutil.which(COMMAND)
        # Then: it is there
        self.assertIsNotNone(found, f"{COMMAND} is not on PATH: {INSTALL_HINT}")

    def test_the_command_on_path_runs_the_code_under_test(self):
        # Given: the command on PATH, and the code in src as it now is
        found = shutil.which(COMMAND)
        self.assertIsNotNone(found, f"{COMMAND} is not on PATH: {INSTALL_HINT}")
        # When: the package the command runs is compared with src, file by file
        installed = installed_package(found)
        source_files = python_files(SOURCE)
        installed_files = python_files(installed)
        differing = sorted(
            name
            for name in source_files.keys() | installed_files.keys()
            if source_files.get(name) != installed_files.get(name)
        )
        # Then: no file differs, so the stories check the code under test, not an earlier build
        self.assertEqual(
            differing,
            [],
            f"{COMMAND} on PATH runs {installed}, which differs from {SOURCE} in "
            f"{', '.join(differing)}: {INSTALL_HINT}",
        )


class SeeMovesStoryTest(StoryTestCase):
    """As the user, I want to see which type folder each file in my Downloads folder, or in a
    folder I name, would go to, with nothing moved."""

    def test_typed_with_nothing_added_it_lists_downloads_and_moves_nothing(self):
        # Given: Downloads holding a photo, an invoice, an installer, a folder, macOS's hidden
        # .DS_Store and a file Chrome is still downloading, as in the README's Example, and home
        # itself holding a file of its own
        make_files(
            self.downloads,
            ["holiday.jpg", "invoice.pdf", "Docker.dmg", ".DS_Store", "report.pdf.crdownload"],
        )
        (self.downloads / "Projects").mkdir()
        make_files(self.home, ["family.png"])
        before = snapshot(self.home)
        # When: organize-downloads is typed with nothing added
        result = run_command(self.home, [])
        # Then: it ends well, lists each of the three files in Downloads with its type folder and
        # nothing else, and every file and folder in home is as it was
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            sorted(listed_moves(result.stdout)),
            [("Docker.dmg", "Installers"), ("holiday.jpg", "Images"), ("invoice.pdf", "Documents")],
        )
        self.assertEqual(snapshot(self.home), before)

    def test_typed_with_a_folder_given_last_it_lists_that_folder_and_moves_nothing(self):
        # Given: a Desktop folder holding a document and an archive, and Downloads holding a photo
        desktop = self.home / "Desktop"
        desktop.mkdir()
        make_files(desktop, ["notes.TXT", "backup.tar.gz"])
        make_files(self.downloads, ["holiday.jpg"])
        before = snapshot(self.home)
        # When: organize-downloads is typed with the Desktop folder given last
        result = run_command(self.home, [str(desktop)])
        # Then: it lists the Desktop files alone, and every file and folder in home is as it was
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            sorted(listed_moves(result.stdout)),
            [("backup.tar.gz", "Archives"), ("notes.TXT", "Documents")],
        )
        self.assertEqual(snapshot(self.home), before)

    # The settings file decides the folder on Linux alone; on macOS the run reads ~/Downloads, so
    # this story has nothing to show there.
    @unittest.skipUnless(sys.platform.startswith("linux"), "xdg-user-dirs settings are Linux's")
    def test_on_linux_with_no_download_folder_named_it_stops_naming_the_settings_file(self):
        # Given: a home on Linux holding Downloads with a file, whose user-dirs settings name no
        # download folder
        settings = write_user_dirs(self.home, 'XDG_DESKTOP_DIR="$HOME/Desktop"\n')
        make_files(self.downloads, ["invoice.pdf"])
        before = snapshot(self.home)
        # When: organize-downloads is typed with nothing added
        result = run_command(self.home, [])
        # Then: it ends with a failing status, names the settings file, lists nothing and
        # changes nothing
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(settings), result.stderr)
        self.assertEqual(listed_moves(result.stdout), [])
        self.assertEqual(snapshot(self.home), before)


class MoveStoryTest(StoryTestCase):
    """As the user, I want to move those files into their type folders when I say so."""

    def test_typed_with_apply_it_moves_each_listed_file_into_its_type_folder(self):
        # Given: Downloads holding a photo, an invoice, an installer, a folder, macOS's hidden
        # .DS_Store and a file Chrome is still downloading, as in the README's Example, and home
        # itself holding a file of its own
        make_files(
            self.downloads,
            ["holiday.jpg", "invoice.pdf", "Docker.dmg", ".DS_Store", "report.pdf.crdownload"],
        )
        (self.downloads / "Projects").mkdir()
        make_files(self.home, ["family.png"])
        before = snapshot(self.home)
        # When: organize-downloads --apply is typed
        result = run_command(self.home, ["--apply"])
        # Then: it ends well and lists each of the three files with its type folder; each is in
        # that type folder inside Downloads under the same name, the record of the moves is in
        # Downloads, and nothing else in home is changed
        self.assertEqual(result.returncode, 0, result.stderr)
        moves = [
            ("Docker.dmg", "Installers"),
            ("holiday.jpg", "Images"),
            ("invoice.pdf", "Documents"),
        ]
        self.assertEqual(sorted(listed_moves(result.stdout)), moves)
        self.assertEqual(
            snapshot_without_record(self.home, "Downloads"), after_moves(before, "Downloads", moves)
        )
        self.assertTrue((self.downloads / RECORD_NAME).is_file())

    def test_typed_with_apply_and_a_folder_given_last_it_moves_that_folder_files(self):
        # Given: a Desktop folder holding a document and an archive, and Downloads holding a photo
        desktop = self.home / "Desktop"
        desktop.mkdir()
        make_files(desktop, ["notes.TXT", "backup.tar.gz"])
        make_files(self.downloads, ["holiday.jpg"])
        before = snapshot(self.home)
        # When: organize-downloads --apply is typed with the Desktop folder given last
        result = run_command(self.home, ["--apply", str(desktop)])
        # Then: the Desktop files alone are moved into their type folders inside Desktop, and
        # nothing else in home is changed, Downloads included
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            snapshot_without_record(self.home, "Desktop"),
            after_moves(
                before, "Desktop", [("backup.tar.gz", "Archives"), ("notes.TXT", "Documents")]
            ),
        )

    def test_a_file_whose_name_is_taken_in_its_type_folder_is_left_and_the_user_told(self):
        # Given: Downloads holding a photo and an invoice, its Documents folder already holding
        # another file named invoice.pdf
        make_files(self.downloads, ["holiday.jpg", "invoice.pdf"])
        (self.downloads / "Documents").mkdir()
        (self.downloads / "Documents" / "invoice.pdf").write_text("filed", encoding="utf-8")
        before = snapshot(self.home)
        # When: organize-downloads --apply is typed
        result = run_command(self.home, ["--apply"])
        # Then: it ends well; the photo is moved, both invoices are as they were, and the output
        # names the invoice and says a file of the same name is already in its type folder
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            snapshot_without_record(self.home, "Downloads"),
            after_moves(before, "Downloads", [("holiday.jpg", "Images")]),
        )
        self.assertIn(("invoice.pdf", "Documents"), listed_moves(result.stdout))
        self.assertIn(NAME_TAKEN_HEADING_END, result.stdout)
