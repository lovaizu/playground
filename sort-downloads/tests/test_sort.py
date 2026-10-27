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
import os
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

    def test_records_the_folder_each_kind_folder_made_and_each_file_moved(
        self,
    ) -> None:
        # Given: a folder holding the README Example's files.
        make_files(self.folder, EXAMPLE_FILES)
        # When: the tool is run on it with --move.
        run_tool(["--move", str(self.folder)])
        # Then: the record names the folder, Images and Others as made, in the
        # order the files needing them were moved, and each file moved with its
        # kind folder; Documents, there before, is not named as made.
        record = json.loads((self.root / RECORD).read_bytes())
        self.assertEqual(
            record,
            {
                "folder": str(self.folder),
                "made": ["Images", "Others"],
                "moved": [
                    {"name": "holiday.jpg", "kind": "Images"},
                    {"name": "invoice.pdf", "kind": "Documents"},
                    {"name": "notes.xyz", "kind": "Others"},
                ],
            },
        )

    def test_leaves_each_file_of_a_kind_whose_folder_name_a_file_takes(
        self,
    ) -> None:
        # Given: a photo, and beside it a file named Images, the name of the
        # photo's kind folder.
        make_files(self.folder, {"holiday.jpg": b"photo", "Images": b"a file"})
        # When: the tool is run on it with --move.
        status, out, err = run_tool(["--move", str(self.folder)])
        # Then: the photo is printed as left, Images being taken, the run goes on to
        # move the file named Images to Others, and both keep their content.
        self.assertEqual(
            out,
            f"In {self.folder}:\n"
            "Moved:\n"
            "  Images -> Others/Images\n"
            "Left:\n"
            "  holiday.jpg: Images already exists\n",
        )
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(
            snapshot(self.folder),
            {"holiday.jpg": b"photo", "Others": None, "Others/Images": b"a file"},
        )

    def test_leaves_each_file_of_a_kind_whose_folder_name_is_saved_after_the_plan(
        self,
    ) -> None:
        # Given: a photo and a PDF, and the user saving a file named Images once the
        # sort is planned, before it moves.
        make_files(self.folder, {"holiday.jpg": b"photo", "invoice.pdf": b"invoice"})
        plan_sort = sort_downloads.plan_sort

        def plan_then_save(folder: Path) -> sort_downloads.SortPlan:
            plan = plan_sort(folder)
            make_files(folder, {"Images": b"saved since"})
            return plan

        # When: the tool is run on it with --move.
        with mock.patch.object(sort_downloads, "plan_sort", plan_then_save):
            status, out, err = run_tool(["--move", str(self.folder)])
        # Then: the photo is printed as left, Images being taken, the PDF still
        # moves, and the file saved keeps its content.
        self.assertIn("  holiday.jpg: Images already exists\n", out)
        self.assertIn("  invoice.pdf -> Documents/invoice.pdf\n", out)
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(
            snapshot(self.folder),
            {
                "holiday.jpg": b"photo",
                "Images": b"saved since",
                "Documents": None,
                "Documents/invoice.pdf": b"invoice",
            },
        )

    def test_moves_a_symbolic_link_as_a_link_leaving_what_it_points_to(
        self,
    ) -> None:
        # Given: a symbolic link ending in .pdf to a file outside the folder.
        make_files(self.root, {"saved/invoice": b"invoice"})
        target = self.root / "saved" / "invoice"
        (self.folder / "invoice.pdf").symlink_to(target)
        # When: the tool is run on the folder with --move.
        run_tool(["--move", str(self.folder)])
        # Then: Documents holds the link, pointing where it did, and the file it
        # points to is where it was with its content.
        moved = self.folder / "Documents" / "invoice.pdf"
        self.assertTrue(moved.is_symlink())
        self.assertEqual(os.readlink(moved), str(target))
        self.assertFalse(os.path.lexists(self.folder / "invoice.pdf"))
        self.assertEqual(target.read_bytes(), b"invoice")

    def test_keeps_the_record_in_home_when_xdg_state_home_is_not_an_absolute_path(
        self,
    ) -> None:
        # Given: a folder holding a photo, run from the temporary folder so a record
        # put at a relative path would land in it.
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        for state in (None, "", "state"):
            with self.subTest(XDG_STATE_HOME=state):
                make_files(self.folder, {"holiday.jpg": b"photo"})
                environment = {} if state is None else {"XDG_STATE_HOME": state}
                with mock.patch.dict(os.environ, environment):
                    if state is None:
                        del os.environ["XDG_STATE_HOME"]
                    # When: the tool is run on it with --move.
                    run_tool(["--move", str(self.folder)])
                # Then: the record is in ~/.local/state/sort-downloads, and nothing
                # is made at XDG_STATE_HOME's place.
                record = self.home / ".local/state/sort-downloads/last-sort.json"
                self.assertEqual(
                    json.loads(record.read_bytes())["folder"], str(self.folder)
                )
                self.assertFalse((self.root / RECORD).exists())
                record.unlink()
                (self.folder / "Images" / "holiday.jpg").unlink()
                (self.folder / "Images").rmdir()

    @unittest.skipIf(
        os.geteuid() == 0, "a folder's permissions do not keep the root user out"
    )
    def test_stops_naming_a_folder_that_cannot_be_changed_and_keeps_the_record(
        self,
    ) -> None:
        # Given: a sort made of another folder, and a folder holding a photo whose
        # permissions let it be read and listed but not changed.
        other = self.root / "other"
        make_files(other, {"invoice.pdf": b"invoice"})
        run_tool(["--move", str(other)])
        make_files(self.folder, {"holiday.jpg": b"photo"})
        before = snapshot(self.root)
        self.addCleanup(self.folder.chmod, 0o755)
        self.folder.chmod(0o555)
        # When: the tool is run on it with --move.
        status, out, err = run_tool(["--move", str(self.folder)])
        # Then: it stops with a failing status, naming the folder and the --move
        # command to name another with, prints nothing on standard output, and
        # leaves everything, the other sort's record among it, as it was.
        self.folder.chmod(0o755)
        self.assertNotEqual(status, 0)
        self.assertIn(str(self.folder), err)
        self.assertIn("sort-downloads --move ~/Desktop", err)
        self.assertEqual(out, "")
        self.assertEqual(snapshot(self.root), before)

    def test_replaces_the_record_of_an_earlier_sort_when_nothing_moves(
        self,
    ) -> None:
        # Given: a sort made of another folder, and a folder holding only a hidden
        # file.
        other = self.root / "other"
        make_files(other, {"invoice.pdf": b"invoice"})
        run_tool(["--move", str(other)])
        make_files(self.folder, {".localized": b""})
        # When: the tool is run on the folder with --move.
        status, out, err = run_tool(["--move", str(self.folder)])
        # Then: it prints the hidden file as left, and the record now names this
        # folder with nothing made or moved, so no undo moves the other's files.
        self.assertEqual(out, f"In {self.folder}:\nLeft:\n  .localized: hidden file\n")
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(
            json.loads((self.root / RECORD).read_bytes()),
            {"folder": str(self.folder), "made": [], "moved": []},
        )

    def test_keeps_in_the_record_what_a_sort_cut_off_part_way_did(self) -> None:
        # Given: a folder holding a photo, a PDF and a file of no listed kind, and
        # the user stopping the run with Ctrl-C as the PDF is given its new name,
        # once Documents is made for it.
        make_files(
            self.folder,
            {"holiday.jpg": b"photo", "invoice.pdf": b"invoice", "notes.xyz": b"notes"},
        )
        link = os.link

        def link_until_the_pdf(old: Path, new: Path, **options: bool) -> None:
            if Path(old).name == "invoice.pdf":
                raise KeyboardInterrupt
            link(old, new, **options)

        # When: the tool is run on it with --move.
        stopping = mock.patch.object(os, "link", link_until_the_pdf)
        with stopping, self.assertRaises(KeyboardInterrupt):
            run_tool(["--move", str(self.folder)])
        # Then: the record holds the folders made, Documents among them, and the
        # photo moved, and the PDF and the other file are where they were.
        self.assertEqual(
            json.loads((self.root / RECORD).read_bytes()),
            {
                "folder": str(self.folder),
                "made": ["Images", "Documents"],
                "moved": [{"name": "holiday.jpg", "kind": "Images"}],
            },
        )
        self.assertEqual(
            snapshot(self.folder),
            {
                "Images": None,
                "Images/holiday.jpg": b"photo",
                "Documents": None,
                "invoice.pdf": b"invoice",
                "notes.xyz": b"notes",
            },
        )

    @unittest.skipIf(
        os.geteuid() == 0, "a folder's permissions do not keep the root user out"
    )
    def test_leaves_a_file_whose_kind_folder_cannot_be_changed_and_moves_the_rest(
        self,
    ) -> None:
        # Given: a PDF and a photo, and a Documents folder there before whose
        # permissions let it be read and listed but not changed.
        make_files(self.folder, {"a.pdf": b"pdf", "b.jpg": b"photo"})
        (self.folder / "Documents").mkdir()
        self.addCleanup((self.folder / "Documents").chmod, 0o755)
        (self.folder / "Documents").chmod(0o555)
        # When: the tool is run on the folder with --move.
        status, out, err = run_tool(["--move", str(self.folder)])
        # Then: the PDF is printed as left, naming where it could not go and the
        # cause, it stays with its content, and the photo still moves and is
        # recorded.
        self.assertEqual(
            out,
            f"In {self.folder}:\n"
            "Moved:\n"
            "  b.jpg -> Images/b.jpg\n"
            "Left:\n"
            "  a.pdf: could not move to Documents/a.pdf: Permission denied\n",
        )
        self.assertEqual((status, err), (0, ""))
        self.assertEqual((self.folder / "a.pdf").read_bytes(), b"pdf")
        self.assertEqual(
            json.loads((self.root / RECORD).read_bytes())["moved"],
            [{"name": "b.jpg", "kind": "Images"}],
        )
