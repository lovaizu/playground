"""Unit tests of the sort: sort-downloads run with --move.

The sort moves each file the preview would move into the folder of its kind, making
that folder where it is not there, leaves each file the preview would leave, and prints
what it did. What it must print and do is drawn from the README's Example, and what it
must move and leave alone from AC2, AC3 and AC4 of the plan
(.rn/20261027-organize-downloads-cli/steering.md); where the record of the sort is kept
is docs/architecture.md's physical view.

Each test runs the tool's main() with the preview's tests' helpers and set-up: on
folders made for it in a temporary folder, with HOME and XDG_STATE_HOME pointed into
that folder, so no test reads or changes the files of the machine it runs on, or
another test's.
"""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import sort_downloads
import tests.test_preview
from tests.test_preview import EXAMPLE_FILES, make_files, run_tool, snapshot

# What the README's Example prints for the files of EXAMPLE_FILES when told to move,
# after the line naming the folder.
EXAMPLE_MOVED = """\
Moved:
  holiday.jpg -> Images/holiday.jpg
  invoice.pdf -> Documents/invoice.pdf
  notes.xyz -> Others/notes.xyz
Left:
  report.pdf: Documents/report.pdf already exists
  .DS_Store: hidden file
  movie.mp4.crdownload: download still running
"""

# The folder of EXAMPLE_FILES once sorted, as the README's Example says: each path
# inside it with a file's content, or None for a folder. Images and Others are made;
# Documents, and Projects, the user's own folder, were there.
EXAMPLE_SORTED: dict[str, bytes | None] = {
    "Images": None,
    "Images/holiday.jpg": b"photo",
    "Documents": None,
    "Documents/invoice.pdf": b"invoice",
    "Documents/report.pdf": b"old report",
    "Others": None,
    "Others/notes.xyz": b"notes",
    "report.pdf": b"new report",
    ".DS_Store": b"finder",
    "movie.mp4.crdownload": b"half a movie",
    "Projects": None,
    "Projects/plan.txt": b"plan",
}

# Where docs/architecture.md's physical view keeps the Last sort record, inside
# XDG_STATE_HOME, with the folder above it.
RECORD = "state/sort-downloads/last-sort.json"


def files_by_name(found: dict[str, bytes | None]) -> Counter[tuple[str, bytes]]:
    """Count the files of a snapshot by name and content, wherever each is.

    Args:
        found: A snapshot, as snapshot() gives it.

    Returns:
        How many files there are of each name, the last part of the path, and
        content; folders are not counted.
    """
    return Counter(
        (Path(path).name, content)
        for path, content in found.items()
        if content is not None
    )


def outside(found: dict[str, bytes | None], name: str) -> dict[str, bytes | None]:
    """Take out of a snapshot a folder directly in its root, and all inside it.

    Args:
        found: A snapshot, as snapshot() gives it.
        name: The folder's name.

    Returns:
        The snapshot's other paths, each with its content or None.
    """
    return {
        path: content for path, content in found.items() if Path(path).parts[0] != name
    }


class TestSort(unittest.TestCase):
    # The preview's tests' set-up, kept in one place: it sets these three paths.
    root: Path
    home: Path
    folder: Path
    setUp = tests.test_preview.TestPreview.setUp

    def test_prints_the_moves_and_the_files_left_as_the_readme_example_shows(
        self,
    ) -> None:
        # Given: a folder holding the README Example's files.
        make_files(self.folder, EXAMPLE_FILES)
        # When: the tool is run on it with --move.
        status, out, err = run_tool(["--move", str(self.folder)])
        # Then: it prints the folder and then what the Example's --move run prints,
        # with no error.
        self.assertEqual(out, f"In {self.folder}:\n{EXAMPLE_MOVED}")
        self.assertEqual((status, err), (0, ""))

    def test_sorts_the_example_folder_as_the_readme_example_shows(self) -> None:
        # Given: a folder holding the README Example's files: images, documents, a
        # file of no listed kind, a name taken in Documents, a subfolder with a file
        # in it, a hidden file and a download still running.
        make_files(self.folder, EXAMPLE_FILES)
        # When: the tool is run on it with --move.
        run_tool(["--move", str(self.folder)])
        # Then: each file it moves is in the folder of its kind, Images and Others
        # made for them; each file it leaves, and the subfolder with its file, is
        # where it was with the same content; and nothing else is there.
        self.assertEqual(snapshot(self.folder), EXAMPLE_SORTED)

    def test_keeps_every_file_there_was_with_its_name_and_content(self) -> None:
        # Given: a folder holding the README Example's files.
        make_files(self.folder, EXAMPLE_FILES)
        before = files_by_name(snapshot(self.folder))
        # When: the tool is run on it with --move.
        run_tool(["--move", str(self.folder)])
        # Then: the folder holds the same files by name and content, as many of each,
        # wherever each now is: none written over, renamed or lost.
        self.assertEqual(files_by_name(snapshot(self.folder)), before)

    def test_works_on_downloads_in_home_when_no_folder_is_named(self) -> None:
        # Given: ~/Downloads holding the README Example's files.
        downloads = self.home / "Downloads"
        make_files(downloads, EXAMPLE_FILES)
        # When: the tool is run with --move and nothing else.
        status, out, err = run_tool(["--move"])
        # Then: it sorts ~/Downloads as the Example shows and prints it so.
        self.assertEqual(out, f"In {downloads}:\n{EXAMPLE_MOVED}")
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(snapshot(downloads), EXAMPLE_SORTED)

    def test_leaves_a_file_whose_name_is_saved_in_its_kind_folder_after_the_plan(
        self,
    ) -> None:
        # Given: a folder holding the README Example's files, and the user saving a
        # new Documents/invoice.pdf once the sort is planned, before it moves.
        make_files(self.folder, EXAMPLE_FILES)
        plan_sort = sort_downloads.plan_sort

        def plan_then_save(folder: Path) -> sort_downloads.SortPlan:
            plan = plan_sort(folder)
            make_files(folder, {"Documents/invoice.pdf": b"saved since"})
            return plan

        # When: the tool is run on it with --move.
        with mock.patch.object(sort_downloads, "plan_sort", plan_then_save):
            status, out, err = run_tool(["--move", str(self.folder)])
        # Then: invoice.pdf is printed as left with the reason and not as moved, it
        # and the file saved keep their content, and the other files still move.
        self.assertIn("  invoice.pdf: Documents/invoice.pdf already exists\n", out)
        self.assertNotIn("invoice.pdf ->", out)
        self.assertEqual((status, err), (0, ""))
        self.assertEqual((self.folder / "invoice.pdf").read_bytes(), b"invoice")
        self.assertEqual(
            (self.folder / "Documents" / "invoice.pdf").read_bytes(), b"saved since"
        )
        self.assertEqual(
            (self.folder / "Images" / "holiday.jpg").read_bytes(), b"photo"
        )

    def test_writes_the_record_of_the_sort_and_nothing_else_outside_the_folder(
        self,
    ) -> None:
        # Given: a folder holding the README Example's files, and no record yet.
        make_files(self.folder, EXAMPLE_FILES)
        before = snapshot(self.root)
        # When: the tool is run on it with --move.
        run_tool(["--move", str(self.folder)])
        # Then: outside the folder, the one thing new is the record, a JSON file in
        # XDG_STATE_HOME's sort-downloads folder, and all else is as it was.
        after = outside(snapshot(self.root), self.folder.name)
        record = after.pop(RECORD, None)
        self.assertIsNotNone(record)
        # b"": for the type checker, as a record of None has failed the line above.
        json.loads(record or b"")
        self.assertEqual(
            after,
            {
                **outside(before, self.folder.name),
                "state": None,
                "state/sort-downloads": None,
            },
        )

    def test_stops_naming_a_folder_that_does_not_exist_and_writes_nothing(
        self,
    ) -> None:
        # Given: a path where there is nothing.
        missing = self.root / "missing"
        before = snapshot(self.root)
        # When: the tool is run on it with --move.
        status, out, err = run_tool(["--move", str(missing)])
        # Then: it stops with a failing status, naming the path, prints nothing on
        # standard output, and makes nothing, no record among it.
        self.assertNotEqual(status, 0)
        self.assertIn(str(missing), err)
        self.assertEqual(out, "")
        self.assertEqual(snapshot(self.root), before)
