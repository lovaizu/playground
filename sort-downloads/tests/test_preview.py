"""Unit tests of the preview: sort-downloads run with no --move.

The preview lists each file lying directly in the folder with the folder of its kind
it would move to, and each file it would leave with the reason, and changes nothing.
What it must print is drawn from the README's Example and its table of kinds, and what
it must leave alone from AC1, AC3 and AC4 of the plan
(.rn/20261027-organize-downloads-cli/steering.md).

Each test runs the tool's main() on folders made for it in a temporary folder, with HOME
and XDG_STATE_HOME pointed into that folder, so no test reads or changes the files of
the machine it runs on, or another test's.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sort_downloads

README = Path(__file__).resolve().parent.parent / "README.md"

# A row of the README's table of kinds whose second cell is a list of endings, such as
# "| Images | .jpg .jpeg |"; the Others row, the heading and the rule under it are not.
KIND_ROW = re.compile(r"^\| (\w+) \| (\.[^|]*?) \|$")

# The files of the README's Example: name and content. Each content differs, so a file
# swapped for another is seen. Projects is the Example's folder of the user's own, whose
# name is no kind, and Documents the kind folder already there.
EXAMPLE_FILES = {
    "holiday.jpg": b"photo",
    "invoice.pdf": b"invoice",
    "notes.xyz": b"notes",
    "report.pdf": b"new report",
    ".DS_Store": b"finder",
    "movie.mp4.crdownload": b"half a movie",
    "Documents/report.pdf": b"old report",
    "Projects/plan.txt": b"plan",
}

# What the README's Example prints for those files, after the line naming the folder.
EXAMPLE_LISTING = """\
Would move:
  holiday.jpg -> Images/holiday.jpg
  invoice.pdf -> Documents/invoice.pdf
  notes.xyz -> Others/notes.xyz
Would leave:
  report.pdf: Documents/report.pdf already exists
  .DS_Store: hidden file
  movie.mp4.crdownload: download still running
Nothing was moved. Run again with --move to move these files.
"""


def readme_kinds() -> dict[str, set[str]]:
    """Read the README's table of kinds.

    Returns:
        Each folder of the table but Others, with the endings of the files going to it.
    """
    kinds: dict[str, set[str]] = {}
    for line in README.read_text(encoding="utf-8").splitlines():
        row = KIND_ROW.match(line)
        if row:
            kinds[row.group(1)] = set(row.group(2).split())
    return kinds


def make_files(folder: Path, files: dict[str, bytes]) -> None:
    """Make each file, and the folders above it, inside the folder.

    Args:
        folder: The folder to make them in.
        files: Each file's path inside the folder, with "/" between parts, and content.
    """
    for name, content in files.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def snapshot(root: Path) -> dict[str, bytes | None]:
    """Read every file and folder under root.

    Args:
        root: The folder to read.

    Returns:
        Each path under root, relative to it, with a file's content or None for a
        folder.
    """
    found: dict[str, bytes | None] = {}
    for path in root.rglob("*"):
        found[str(path.relative_to(root))] = (
            None if path.is_dir() else path.read_bytes()
        )
    return found


def run_tool(argv: list[str]) -> tuple[int, str, str]:
    """Run the tool as its command would, with the arguments after the command name.

    Args:
        argv: The arguments, such as ["--move", "/some/folder"].

    Returns:
        The exit status, what it printed to standard output and what to standard error.
        A stop by SystemExit gives the status the shell would see: 0 for no code, the
        code where it is a number, and 1 for a message.
    """
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = sort_downloads.main(argv)
        except SystemExit as stop:
            code = stop.code
            status = 0 if code is None else code if isinstance(code, int) else 1
    return status, out.getvalue(), err.getvalue()


class TestPreview(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        # realpath: the folder's own path, the one the tool prints, where the temporary
        # folder is reached through a symbolic link, as /var is on macOS.
        self.root = Path(os.path.realpath(temporary.name))
        self.home = self.root / "home"
        self.home.mkdir()
        environment = {
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.root / "state"),
        }
        patch = mock.patch.dict(os.environ, environment)
        patch.start()
        self.addCleanup(patch.stop)
        self.folder = self.root / "trial"
        self.folder.mkdir()

    def test_lists_the_example_folder_as_the_readme_example_shows(self) -> None:
        # Given: a folder holding the README Example's files.
        make_files(self.folder, EXAMPLE_FILES)
        # When: the tool is run on it with no --move.
        status, out, err = run_tool([str(self.folder)])
        # Then: it prints the folder and then the Example's listing, with no error.
        self.assertEqual(out, f"In {self.folder}:\n{EXAMPLE_LISTING}")
        self.assertEqual((status, err), (0, ""))

    def test_leaves_every_file_and_folder_where_it_was_unchanged(self) -> None:
        # Given: a folder holding the README Example's files, among them subfolders
        # with a file in each and a name already taken in the folder it would go to.
        make_files(self.folder, EXAMPLE_FILES)
        before = snapshot(self.root)
        # When: the tool is run on it with no --move.
        run_tool([str(self.folder)])
        # Then: every file and folder under the temporary folder, the record's place
        # among them, is there with the same name and content, and nothing else is.
        self.assertEqual(snapshot(self.root), before)

    def test_works_on_downloads_in_home_when_no_folder_is_named(self) -> None:
        # Given: ~/Downloads holding the README Example's files.
        downloads = self.home / "Downloads"
        make_files(downloads, EXAMPLE_FILES)
        before = snapshot(self.root)
        # When: the tool is run with nothing after it.
        status, out, err = run_tool([])
        # Then: it lists ~/Downloads as the Example shows and leaves it unchanged.
        self.assertEqual(out, f"In {downloads}:\n{EXAMPLE_LISTING}")
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(snapshot(self.root), before)

    def test_holds_the_kinds_and_endings_of_the_readme_table(self) -> None:
        # Given: the README's table of kinds and endings.
        table = readme_kinds()
        # When: the kinds the tool holds are read.
        held = {
            folder: set(endings) for folder, endings in sort_downloads.KINDS.items()
        }
        # Then: they are the table's, Others aside.
        self.assertEqual(held, table)

    def test_would_move_each_file_by_its_ending_to_its_kind_in_the_readme_table(
        self,
    ) -> None:
        # Given: a file for each ending the README's table lists.
        table = readme_kinds()
        make_files(
            self.folder,
            {f"file{ending}": b"" for endings in table.values() for ending in endings},
        )
        # When: the tool is run on the folder with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: each file is listed as moving to the folder of its ending.
        for folder, endings in table.items():
            for ending in endings:
                self.assertIn(f"  file{ending} -> {folder}/file{ending}\n", out)

    def test_counts_capital_letters_in_an_ending_the_same_as_small_ones(self) -> None:
        # Given: a photo whose ending is written in capitals.
        make_files(self.folder, {"IMG_0001.JPG": b"photo"})
        # When: the tool is run on the folder with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: it is listed as moving to Images, keeping its name.
        self.assertIn("  IMG_0001.JPG -> Images/IMG_0001.JPG\n", out)

    def test_would_move_a_file_of_no_ending_to_others(self) -> None:
        # Given: a file whose name has no ending.
        make_files(self.folder, {"LICENSE": b"text"})
        # When: the tool is run on the folder with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: it is listed as moving to Others.
        self.assertIn("  LICENSE -> Others/LICENSE\n", out)

    def test_would_leave_each_hidden_file_and_download_still_running(self) -> None:
        # Given: a hidden file and a download of each browser the README names.
        make_files(
            self.folder,
            {
                ".localized": b"",
                "album.zip.crdownload": b"chrome",
                "video.mkv.part": b"firefox",
            },
        )
        # When: the tool is run on the folder with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: each is listed as left, with its reason.
        self.assertIn("  .localized: hidden file\n", out)
        self.assertIn("  album.zip.crdownload: download still running\n", out)
        self.assertIn("  video.mkv.part: download still running\n", out)

    def test_goes_by_the_last_ending_when_a_download_ending_is_earlier(self) -> None:
        # Given: a file whose name holds ".part" but ends in ".txt".
        make_files(self.folder, {"draft.part.txt": b"text"})
        # When: the tool is run on the folder with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: it is listed as moving to Documents, not as a download still running.
        self.assertIn("  draft.part.txt -> Documents/draft.part.txt\n", out)

    def test_stops_naming_a_folder_that_does_not_exist(self) -> None:
        # Given: a path where there is nothing.
        missing = self.root / "missing"
        before = snapshot(self.root)
        # When: the tool is run on it with no --move.
        status, out, err = run_tool([str(missing)])
        # Then: it stops with a failing status, naming the path, lists nothing, and
        # makes nothing.
        self.assertNotEqual(status, 0)
        self.assertIn(str(missing), err)
        self.assertEqual(out, "")
        self.assertEqual(snapshot(self.root), before)

    def test_stops_naming_a_path_that_is_a_file_not_a_folder(self) -> None:
        # Given: a file where a folder is named.
        make_files(self.folder, {"holiday.jpg": b"photo"})
        named = self.folder / "holiday.jpg"
        before = snapshot(self.root)
        # When: the tool is run on the file with no --move.
        status, out, err = run_tool([str(named)])
        # Then: it stops with a failing status, naming the path, lists nothing, and
        # changes nothing.
        self.assertNotEqual(status, 0)
        self.assertIn(str(named), err)
        self.assertEqual(out, "")
        self.assertEqual(snapshot(self.root), before)

    def test_stops_naming_an_option_it_does_not_take(self) -> None:
        # Given: a folder holding the README Example's files.
        make_files(self.folder, EXAMPLE_FILES)
        before = snapshot(self.root)
        # When: the tool is run with a misspelt option.
        status, out, err = run_tool(["--mvoe", str(self.folder)])
        # Then: it stops with a failing status, naming the option, lists nothing, and
        # changes nothing.
        self.assertNotEqual(status, 0)
        self.assertIn("--mvoe", err)
        self.assertEqual(out, "")
        self.assertEqual(snapshot(self.root), before)

    @unittest.skipIf(
        os.geteuid() == 0, "a folder's permissions do not keep the root user out"
    )
    def test_stops_naming_a_folder_that_cannot_be_read(self) -> None:
        # Given: a folder holding a file, whose permissions let its owner do nothing,
        # only list it without opening what is in it, or only open what is in it
        # without listing it.
        make_files(self.folder, {"holiday.jpg": b"photo"})
        before = snapshot(self.root)
        self.addCleanup(self.folder.chmod, 0o755)
        for mode in (0o000, 0o600, 0o300):
            with self.subTest(mode=oct(mode)):
                self.folder.chmod(mode)
                # When: the tool is run on it with no --move.
                status, out, err = run_tool([str(self.folder)])
                # Then: it stops with a failing status, naming the folder, and lists
                # nothing; once it can be read again, the folder is as it was.
                self.folder.chmod(0o755)
                self.assertNotEqual(status, 0)
                self.assertIn(str(self.folder), err)
                self.assertEqual(out, "")
                self.assertEqual(snapshot(self.root), before)

    def test_stops_naming_the_second_of_two_folders(self) -> None:
        # Given: two folders, each holding a file.
        other = self.root / "other"
        make_files(self.folder, {"holiday.jpg": b"photo"})
        make_files(other, {"invoice.pdf": b"invoice"})
        before = snapshot(self.root)
        # When: the tool is run on both with no --move.
        status, out, err = run_tool([str(self.folder), str(other)])
        # Then: it stops with a failing status, naming the second, lists nothing, and
        # changes nothing.
        self.assertNotEqual(status, 0)
        self.assertIn(str(other), err)
        self.assertEqual(out, "")
        self.assertEqual(snapshot(self.root), before)

    def test_leaves_out_a_link_to_a_folder(self) -> None:
        # Given: a photo, and a symbolic link to a folder elsewhere holding a file.
        make_files(self.folder, {"holiday.jpg": b"photo"})
        make_files(self.root / "elsewhere", {"plan.txt": b"plan"})
        (self.folder / "shortcut").symlink_to(self.root / "elsewhere")
        # When: the tool is run on the folder with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: only the photo is listed, the link no more than a folder is.
        self.assertEqual(
            out,
            f"In {self.folder}:\n"
            "Would move:\n"
            "  holiday.jpg -> Images/holiday.jpg\n"
            "Nothing was moved. Run again with --move to move these files.\n",
        )

    def test_would_move_a_link_to_a_file_by_the_link_s_ending(self) -> None:
        # Given: a symbolic link ending in .pdf to a file elsewhere.
        make_files(self.root, {"saved/invoice": b"invoice"})
        (self.folder / "invoice.pdf").symlink_to(self.root / "saved" / "invoice")
        # When: the tool is run on the folder with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: the link is listed as moving to Documents, as a file of its name is.
        self.assertIn("  invoice.pdf -> Documents/invoice.pdf\n", out)

    def test_would_leave_a_file_whose_name_a_link_to_nothing_takes(self) -> None:
        # Given: a PDF, and in Documents a symbolic link of the same name to nothing.
        make_files(self.folder, {"report.pdf": b"new report"})
        (self.folder / "Documents").mkdir()
        (self.folder / "Documents" / "report.pdf").symlink_to(self.root / "gone")
        # When: the tool is run on the folder with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: the PDF is listed as left, its name taken.
        self.assertIn("  report.pdf: Documents/report.pdf already exists\n", out)
        self.assertNotIn("report.pdf ->", out)

    def test_prints_only_the_folder_and_that_nothing_moved_for_an_empty_folder(
        self,
    ) -> None:
        # Given: an empty folder.
        # When: the tool is run on it with no --move.
        status, out, err = run_tool([str(self.folder)])
        # Then: it prints the folder and that nothing was moved, with no heading and
        # no word of --move, as there is nothing to move.
        self.assertEqual(out, f"In {self.folder}:\nNothing was moved.\n")
        self.assertEqual((status, err), (0, ""))

    def test_prints_no_move_heading_nor_move_hint_when_every_file_is_left(
        self,
    ) -> None:
        # Given: a folder holding only a hidden file.
        make_files(self.folder, {".localized": b""})
        # When: the tool is run on it with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: it prints the file under "Would leave" alone, and no word of --move.
        self.assertEqual(
            out,
            f"In {self.folder}:\n"
            "Would leave:\n"
            "  .localized: hidden file\n"
            "Nothing was moved.\n",
        )

    def test_lists_names_in_order_counting_capitals_as_small_letters(self) -> None:
        # Given: files whose order by character code, capitals first, differs from
        # their order counting capitals as small letters.
        make_files(
            self.folder, {"Zebra.txt": b"z", "apple.txt": b"a", "Mango.txt": b""}
        )
        # When: the tool is run on the folder with no --move.
        out = run_tool([str(self.folder)])[1]
        # Then: they are listed as a person reads them: apple, Mango, Zebra.
        self.assertIn(
            "Would move:\n"
            "  apple.txt -> Documents/apple.txt\n"
            "  Mango.txt -> Documents/Mango.txt\n"
            "  Zebra.txt -> Documents/Zebra.txt\n",
            out,
        )
