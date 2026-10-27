"""Unit tests of the undo: sort-downloads run with --undo, and with --undo --move.

The undo works on the last sort, the last run told to move that was not an undo,
in whichever folder that sort was, so no folder is named with it. Without --move it
lists each file that sort moved with the place it would go back to, and each file it
would leave with the reason, and changes nothing; with --move it moves each file back,
one by one, and removes each folder that sort made once it is empty. What it must
print and do is drawn from the README's Example, and what it must move, leave and
remove from AC3, AC4 and AC8 of the plan (.rn/20261027-organize-downloads-cli/
steering.md); that a later undo goes on with what an earlier one left, and that a
file saved since the plan is never written over, is docs/architecture.md's Mover.

Each test runs the tool's main() with the preview's tests' helpers and set-up: on
folders made for it in a temporary folder, with HOME and XDG_STATE_HOME pointed into
that folder, so no test reads or changes the files of the machine it runs on, or
another test's.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import sort_downloads
import tests.test_preview
from tests.test_preview import EXAMPLE_FILES, make_files, run_tool, snapshot
from tests.test_sort import files_by_name

# The new notes.xyz of the README's Example, saved in the folder after the sort where
# the one the sort moved to Others was.
NEW_NOTES = {"notes.xyz": b"new notes"}

# The last line the undo prints without --move where it would move a file back.
NOTHING_MOVED_BACK = (
    "Nothing was moved. Run again with --undo --move to move these files back.\n"
)

# What the README's Example prints for the undo without --move, after the line naming
# the folder.
EXAMPLE_UNDO_LISTING = f"""\
Would move back:
  Images/holiday.jpg -> holiday.jpg
  Documents/invoice.pdf -> invoice.pdf
Would leave:
  Others/notes.xyz: notes.xyz already exists
{NOTHING_MOVED_BACK}"""

# What the README's Example prints for the undo with --move, after the line naming the
# folder.
EXAMPLE_UNDONE_LISTING = """\
Moved back:
  Images/holiday.jpg -> holiday.jpg
  Documents/invoice.pdf -> invoice.pdf
Left:
  Others/notes.xyz: notes.xyz already exists
Removed empty folder:
  Images
"""

# The folder of the README's Example once undone: the photo and the invoice back
# where they were, the new notes.xyz kept and the one the sort moved left in Others;
# Images, made by the sort and then empty, removed; Others, still holding a file, and
# Documents, there before the sort, kept.
EXAMPLE_UNDONE: dict[str, bytes | None] = {
    "holiday.jpg": b"photo",
    "invoice.pdf": b"invoice",
    "notes.xyz": b"new notes",
    "report.pdf": b"new report",
    ".DS_Store": b"finder",
    "movie.mp4.crdownload": b"half a movie",
    "Documents": None,
    "Documents/report.pdf": b"old report",
    "Others": None,
    "Others/notes.xyz": b"notes",
    "Projects": None,
    "Projects/plan.txt": b"plan",
}


def snapshot_of(files: dict[str, bytes]) -> dict[str, bytes | None]:
    """Give the snapshot of a folder holding the files, as make_files() makes them.

    Args:
        files: Each file's path inside the folder, with "/" between parts, and content.

    Returns:
        Each file with its content, and each folder above one with None, as snapshot()
        gives them.
    """
    found: dict[str, bytes | None] = {}
    for name, content in files.items():
        for folder in list(Path(name).parents)[:-1]:
            found[str(folder)] = None
        found[name] = content
    return found


class TestUndo(unittest.TestCase):
    # The preview's tests' set-up, kept in one place: it sets these three paths.
    root: Path
    home: Path
    folder: Path
    setUp = tests.test_preview.TestPreview.setUp

    def sort_the_example_then_save_new_notes(self) -> None:
        """Make the README Example's files in the folder, sort it, then save notes.xyz.

        This is the folder the README's Example undoes, AC4's trial folder after a
        sort: a new file of the same name as one the sort moved, put where that one
        was.
        """
        make_files(self.folder, EXAMPLE_FILES)
        run_tool(["--move", str(self.folder)])
        make_files(self.folder, NEW_NOTES)

    def test_lists_the_example_undo_as_the_readme_example_shows(self) -> None:
        # Given: the README Example's folder, sorted, then given a new notes.xyz.
        self.sort_the_example_then_save_new_notes()
        # When: the tool is run with --undo.
        status, out, err = run_tool(["--undo"])
        # Then: it prints the folder and then the Example's undo listing, with no
        # error.
        self.assertEqual(out, f"In {self.folder}:\n{EXAMPLE_UNDO_LISTING}")
        self.assertEqual((status, err), (0, ""))

    def test_undo_without_move_leaves_every_file_folder_and_the_record_as_it_was(
        self,
    ) -> None:
        # Given: the README Example's folder, sorted, then given a new notes.xyz.
        self.sort_the_example_then_save_new_notes()
        before = snapshot(self.root)
        # When: the tool is run with --undo.
        run_tool(["--undo"])
        # Then: every file and folder under the temporary folder, the record among
        # them, is there with the same name and content, and nothing else is.
        self.assertEqual(snapshot(self.root), before)

    def test_prints_the_moves_back_and_folders_removed_as_the_readme_example_shows(
        self,
    ) -> None:
        # Given: the README Example's folder, sorted, then given a new notes.xyz.
        self.sort_the_example_then_save_new_notes()
        # When: the tool is run with --undo --move.
        status, out, err = run_tool(["--undo", "--move"])
        # Then: it prints the folder and then what the Example's --undo --move run
        # prints, with no error.
        self.assertEqual(out, f"In {self.folder}:\n{EXAMPLE_UNDONE_LISTING}")
        self.assertEqual((status, err), (0, ""))

    def test_undoes_the_example_folder_as_the_readme_example_shows(self) -> None:
        # Given: the README Example's folder, sorted, then given a new notes.xyz.
        self.sort_the_example_then_save_new_notes()
        # When: the tool is run with --undo --move.
        run_tool(["--undo", "--move"])
        # Then: the photo and the invoice are back where they were, both notes.xyz
        # keep their places and content, Images is removed, Others and Documents
        # stay, and nothing else is there.
        self.assertEqual(snapshot(self.folder), EXAMPLE_UNDONE)

    def test_keeps_every_file_there_was_with_its_name_and_content(self) -> None:
        # Given: the README Example's folder, sorted, then given a new notes.xyz.
        self.sort_the_example_then_save_new_notes()
        before = files_by_name(snapshot(self.folder))
        # When: the tool is run with --undo --move.
        run_tool(["--undo", "--move"])
        # Then: the folder holds the same files by name and content, as many of each,
        # wherever each now is: none written over, renamed or lost.
        self.assertEqual(files_by_name(snapshot(self.folder)), before)

    def test_puts_the_folder_back_as_it_was_before_the_sort(self) -> None:
        # Given: the README Example's folder, sorted, with nothing saved since.
        make_files(self.folder, EXAMPLE_FILES)
        before = snapshot(self.folder)
        run_tool(["--move", str(self.folder)])
        # When: the tool is run with --undo --move.
        status, out, err = run_tool(["--undo", "--move"])
        # Then: it prints each file moved back and both folders the sort made as
        # removed, in the order the sort made them, and the folder is as it was
        # before the sort.
        self.assertEqual(
            out,
            f"In {self.folder}:\n"
            "Moved back:\n"
            "  Images/holiday.jpg -> holiday.jpg\n"
            "  Documents/invoice.pdf -> invoice.pdf\n"
            "  Others/notes.xyz -> notes.xyz\n"
            "Removed empty folder:\n"
            "  Images\n"
            "  Others\n",
        )
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(snapshot(self.folder), before)

    def test_undoes_the_sort_of_downloads_in_home_made_with_no_folder_named(
        self,
    ) -> None:
        # Given: ~/Downloads holding the README Example's files, sorted by the tool
        # run with --move and nothing else.
        downloads = self.home / "Downloads"
        make_files(downloads, EXAMPLE_FILES)
        before = snapshot(downloads)
        run_tool(["--move"])
        # When: the tool is run with --undo --move.
        status, out, err = run_tool(["--undo", "--move"])
        # Then: its first line names ~/Downloads, and ~/Downloads is as it was before
        # the sort.
        self.assertEqual(out.splitlines()[0], f"In {downloads}:")
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(snapshot(downloads), before)

    def test_undoes_the_sorted_folder_not_downloads_in_home(self) -> None:
        # Given: ~/Downloads holding a photo, and the README Example's folder, named
        # to the tool, sorted.
        downloads = self.home / "Downloads"
        make_files(downloads, {"holiday.jpg": b"photo in downloads"})
        make_files(self.folder, EXAMPLE_FILES)
        run_tool(["--move", str(self.folder)])
        before = snapshot(downloads)
        # When: the tool is run with --undo --move.
        out = run_tool(["--undo", "--move"])[1]
        # Then: its first line names the sorted folder, that folder is as it was
        # before the sort, and ~/Downloads is unchanged.
        self.assertEqual(out.splitlines()[0], f"In {self.folder}:")
        self.assertEqual(snapshot(self.folder), snapshot_of(EXAMPLE_FILES))
        self.assertEqual(snapshot(downloads), before)

    def test_undoes_only_the_last_of_two_sorts(self) -> None:
        # Given: a sort of another folder holding a PDF, then a sort of the folder
        # holding a photo.
        other = self.root / "other"
        make_files(other, {"invoice.pdf": b"invoice"})
        run_tool(["--move", str(other)])
        make_files(self.folder, {"holiday.jpg": b"photo"})
        run_tool(["--move", str(self.folder)])
        # When: the tool is run with --undo --move.
        out = run_tool(["--undo", "--move"])[1]
        # Then: the photo is moved back, and the other folder's PDF stays sorted.
        self.assertEqual(
            out,
            f"In {self.folder}:\n"
            "Moved back:\n"
            "  Images/holiday.jpg -> holiday.jpg\n"
            "Removed empty folder:\n"
            "  Images\n",
        )
        self.assertEqual(snapshot(self.folder), {"holiday.jpg": b"photo"})
        self.assertEqual(
            snapshot(other),
            {"Documents": None, "Documents/invoice.pdf": b"invoice"},
        )

    def test_a_run_without_move_after_the_sort_does_not_change_which_is_undone(
        self,
    ) -> None:
        # Given: a sort of the folder holding a photo, then a run without --move on
        # another folder holding a PDF.
        make_files(self.folder, {"holiday.jpg": b"photo"})
        run_tool(["--move", str(self.folder)])
        other = self.root / "other"
        make_files(other, {"invoice.pdf": b"invoice"})
        run_tool([str(other)])
        # When: the tool is run with --undo.
        out = run_tool(["--undo"])[1]
        # Then: it lists the sort of the folder, the photo moving back.
        self.assertEqual(
            out,
            f"In {self.folder}:\n"
            "Would move back:\n"
            "  Images/holiday.jpg -> holiday.jpg\n"
            f"{NOTHING_MOVED_BACK}",
        )

    def test_a_later_undo_moves_back_a_file_left_once_its_place_is_cleared(
        self,
    ) -> None:
        # Given: the README Example's folder, sorted, given a new notes.xyz, and
        # undone with --move, leaving Others/notes.xyz; then the new notes.xyz moved
        # out of the folder by the user.
        self.sort_the_example_then_save_new_notes()
        run_tool(["--undo", "--move"])
        (self.folder / "notes.xyz").rename(self.root / "notes.xyz")
        # When: the tool is run with --undo, then with --undo --move.
        listing = run_tool(["--undo"])[1]
        status, out, err = run_tool(["--undo", "--move"])
        # Then: each run works on that sort still, for the file left alone: it is
        # listed, then moved back, and Others, then empty, is removed.
        self.assertEqual(
            listing,
            f"In {self.folder}:\n"
            "Would move back:\n"
            "  Others/notes.xyz -> notes.xyz\n"
            f"{NOTHING_MOVED_BACK}",
        )
        self.assertEqual(
            out,
            f"In {self.folder}:\n"
            "Moved back:\n"
            "  Others/notes.xyz -> notes.xyz\n"
            "Removed empty folder:\n"
            "  Others\n",
        )
        self.assertEqual((status, err), (0, ""))
        self.assertEqual((self.folder / "notes.xyz").read_bytes(), b"notes")
        self.assertNotIn("Others", snapshot(self.folder))

    def test_an_undo_after_everything_is_moved_back_lists_nothing(self) -> None:
        # Given: the README Example's folder, sorted, then undone with --move.
        make_files(self.folder, EXAMPLE_FILES)
        run_tool(["--move", str(self.folder)])
        run_tool(["--undo", "--move"])
        before = snapshot(self.root)
        # When: the tool is run with --undo, then with --undo --move.
        listing = run_tool(["--undo"])[1]
        status, out, err = run_tool(["--undo", "--move"])
        # Then: the first prints the folder and that nothing was moved, with no word
        # of --move, the second the folder alone, and nothing is changed.
        self.assertEqual(listing, f"In {self.folder}:\nNothing was moved.\n")
        self.assertEqual(out, f"In {self.folder}:\n")
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(snapshot(self.root), before)

    def test_keeps_a_folder_there_before_the_sort_though_it_is_left_empty(
        self,
    ) -> None:
        # Given: a folder holding a PDF and an empty Documents folder, sorted.
        make_files(self.folder, {"invoice.pdf": b"invoice"})
        (self.folder / "Documents").mkdir()
        run_tool(["--move", str(self.folder)])
        # When: the tool is run with --undo --move.
        out = run_tool(["--undo", "--move"])[1]
        # Then: the PDF is moved back and Documents, empty again, is kept and not
        # printed as removed.
        self.assertEqual(
            out,
            f"In {self.folder}:\nMoved back:\n  Documents/invoice.pdf -> invoice.pdf\n",
        )
        self.assertEqual(
            snapshot(self.folder), {"invoice.pdf": b"invoice", "Documents": None}
        )

    def test_keeps_a_folder_the_sort_made_that_still_holds_a_file_saved_since(
        self,
    ) -> None:
        # Given: a folder holding a photo, sorted, then a new photo saved by the user
        # in Images, the folder the sort made.
        make_files(self.folder, {"holiday.jpg": b"photo"})
        run_tool(["--move", str(self.folder)])
        make_files(self.folder, {"Images/beach.png": b"new photo"})
        # When: the tool is run with --undo --move.
        out = run_tool(["--undo", "--move"])[1]
        # Then: the photo the sort moved is moved back, and the new photo, which the
        # sort did not move, stays in Images, which is kept and not printed as
        # removed.
        self.assertEqual(
            out,
            f"In {self.folder}:\nMoved back:\n  Images/holiday.jpg -> holiday.jpg\n",
        )
        self.assertEqual(
            snapshot(self.folder),
            {
                "holiday.jpg": b"photo",
                "Images": None,
                "Images/beach.png": b"new photo",
            },
        )

    def test_leaves_a_file_whose_old_place_is_taken_after_the_plan(self) -> None:
        # Given: the README Example's folder, sorted, and the user saving a new
        # invoice.pdf where the sort's one was once the undo is planned, before it
        # moves.
        make_files(self.folder, EXAMPLE_FILES)
        run_tool(["--move", str(self.folder)])
        plan_undo = sort_downloads.plan_undo

        def plan_then_save(*arguments: Any, **options: Any) -> Any:
            plan = plan_undo(*arguments, **options)
            make_files(self.folder, {"invoice.pdf": b"saved since"})
            return plan

        # When: the tool is run with --undo --move.
        with mock.patch.object(sort_downloads, "plan_undo", plan_then_save):
            status, out, err = run_tool(["--undo", "--move"])
        # Then: invoice.pdf is printed as left with the reason and not as moved back,
        # it and the file saved keep their content, the others still move back, and
        # Documents, there before the sort, stays.
        self.assertIn("  Documents/invoice.pdf: invoice.pdf already exists\n", out)
        self.assertNotIn("Documents/invoice.pdf ->", out)
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(
            (self.folder / "Documents" / "invoice.pdf").read_bytes(), b"invoice"
        )
        self.assertEqual((self.folder / "invoice.pdf").read_bytes(), b"saved since")
        self.assertEqual((self.folder / "holiday.jpg").read_bytes(), b"photo")

    def test_keeps_a_folder_the_sort_made_that_is_given_a_file_after_the_plan(
        self,
    ) -> None:
        # Given: a folder holding a photo, sorted, and the user saving a new photo in
        # Images once the undo is planned, before it moves.
        make_files(self.folder, {"holiday.jpg": b"photo"})
        run_tool(["--move", str(self.folder)])
        plan_undo = sort_downloads.plan_undo

        def plan_then_save(*arguments: Any, **options: Any) -> Any:
            plan = plan_undo(*arguments, **options)
            make_files(self.folder, {"Images/beach.png": b"new photo"})
            return plan

        # When: the tool is run with --undo --move.
        with mock.patch.object(sort_downloads, "plan_undo", plan_then_save):
            status, out, err = run_tool(["--undo", "--move"])
        # Then: the photo is moved back, Images is kept with the new photo in it,
        # and Images is not printed as removed.
        self.assertEqual(
            out,
            f"In {self.folder}:\nMoved back:\n  Images/holiday.jpg -> holiday.jpg\n",
        )
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(
            snapshot(self.folder),
            {
                "holiday.jpg": b"photo",
                "Images": None,
                "Images/beach.png": b"new photo",
            },
        )

    def test_leaves_a_file_the_sort_moved_that_is_no_longer_there(self) -> None:
        # Given: a folder holding a photo and a PDF, sorted, then the photo moved
        # out of Images by the user.
        make_files(self.folder, {"holiday.jpg": b"photo", "invoice.pdf": b"invoice"})
        run_tool(["--move", str(self.folder)])
        (self.folder / "Images" / "holiday.jpg").rename(self.root / "holiday.jpg")
        # When: the tool is run with --undo, then with --undo --move.
        listing = run_tool(["--undo"])[1]
        status, out, err = run_tool(["--undo", "--move"])
        # Then: each lists the photo as left, as it is no longer there, and moves
        # back the PDF; Images and Documents, made by the sort and then empty, are
        # removed.
        self.assertEqual(
            listing,
            f"In {self.folder}:\n"
            "Would move back:\n"
            "  Documents/invoice.pdf -> invoice.pdf\n"
            "Would leave:\n"
            "  Images/holiday.jpg: no longer there\n"
            f"{NOTHING_MOVED_BACK}",
        )
        self.assertEqual(
            out,
            f"In {self.folder}:\n"
            "Moved back:\n"
            "  Documents/invoice.pdf -> invoice.pdf\n"
            "Left:\n"
            "  Images/holiday.jpg: no longer there\n"
            "Removed empty folder:\n"
            "  Images\n"
            "  Documents\n",
        )
        self.assertEqual((status, err), (0, ""))
        self.assertEqual(snapshot(self.folder), {"invoice.pdf": b"invoice"})

    def test_keeps_what_an_undo_cut_off_part_way_left_to_undo(self) -> None:
        # Given: the README Example's folder, sorted, and the user stopping the undo
        # with Ctrl-C as the PDF is given back its old name, once the photo is back.
        make_files(self.folder, EXAMPLE_FILES)
        run_tool(["--move", str(self.folder)])
        link = os.link

        def link_until_the_pdf(old: Path, new: Path, **options: bool) -> None:
            if Path(old).name == "invoice.pdf":
                raise KeyboardInterrupt
            link(old, new, **options)

        stopping = mock.patch.object(os, "link", link_until_the_pdf)
        with stopping, self.assertRaises(KeyboardInterrupt):
            run_tool(["--undo", "--move"])
        # When: the tool is run with --undo, then with --undo --move.
        listing = run_tool(["--undo"])[1]
        run_tool(["--undo", "--move"])
        # Then: the first lists only the files still to move back, and after the
        # second the folder is as it was before the sort.
        self.assertEqual(
            listing,
            f"In {self.folder}:\n"
            "Would move back:\n"
            "  Documents/invoice.pdf -> invoice.pdf\n"
            "  Others/notes.xyz -> notes.xyz\n"
            f"{NOTHING_MOVED_BACK}",
        )
        self.assertEqual(snapshot(self.folder), snapshot_of(EXAMPLE_FILES))

    def test_stops_when_no_sort_has_been_made(self) -> None:
        # Given: a folder holding the README Example's files, never sorted, and no
        # record.
        make_files(self.folder, EXAMPLE_FILES)
        before = snapshot(self.root)
        for argv in (["--undo"], ["--undo", "--move"]):
            with self.subTest(argv=argv):
                # When: the tool is run with --undo, with or without --move.
                status, out, err = run_tool(argv)
                # Then: it stops with a failing status, naming the command a sort to
                # undo is made with, which the usage line it prints does not hold,
                # prints nothing on standard output, and makes nothing.
                self.assertNotEqual(status, 0)
                self.assertIn("sort-downloads --move", err)
                self.assertEqual(out, "")
                self.assertEqual(snapshot(self.root), before)

    def test_stops_naming_the_sorted_folder_when_it_is_gone(self) -> None:
        # Given: a folder holding a photo, sorted, then moved away by the user.
        make_files(self.folder, {"holiday.jpg": b"photo"})
        run_tool(["--move", str(self.folder)])
        self.folder.rename(self.root / "moved")
        before = snapshot(self.root)
        for argv in (["--undo"], ["--undo", "--move"]):
            with self.subTest(argv=argv):
                # When: the tool is run with --undo, with or without --move.
                status, out, err = run_tool(argv)
                # Then: it stops with a failing status, naming the folder, prints
                # nothing on standard output, and changes nothing.
                self.assertNotEqual(status, 0)
                self.assertIn(str(self.folder), err)
                self.assertEqual(out, "")
                self.assertEqual(snapshot(self.root), before)

    def test_stops_naming_a_folder_given_with_undo(self) -> None:
        # Given: the README Example's folder, sorted.
        make_files(self.folder, EXAMPLE_FILES)
        run_tool(["--move", str(self.folder)])
        before = snapshot(self.root)
        for argv in (
            ["--undo", str(self.folder)],
            ["--undo", "--move", str(self.folder)],
        ):
            with self.subTest(argv=argv):
                # When: the tool is run with --undo and a folder named, with or
                # without --move.
                status, out, err = run_tool(argv)
                # Then: it stops with a failing status, naming the folder, as the
                # undo takes none, prints nothing on standard output, and changes
                # nothing.
                self.assertNotEqual(status, 0)
                self.assertIn(str(self.folder), err)
                self.assertEqual(out, "")
                self.assertEqual(snapshot(self.root), before)

    @unittest.skipIf(
        os.geteuid() == 0, "a folder's permissions do not keep the root user out"
    )
    def test_stops_naming_the_sorted_folder_when_it_cannot_be_changed(self) -> None:
        # Given: a folder holding a photo, sorted, then given permissions that let
        # it be read and listed but not changed.
        make_files(self.folder, {"holiday.jpg": b"photo"})
        run_tool(["--move", str(self.folder)])
        before = snapshot(self.root)
        self.addCleanup(self.folder.chmod, 0o755)
        self.folder.chmod(0o555)
        # When: the tool is run with --undo --move.
        status, out, err = run_tool(["--undo", "--move"])
        # Then: it stops with a failing status, naming the folder, prints nothing on
        # standard output, and leaves everything, the record among it, as it was.
        self.folder.chmod(0o755)
        self.assertNotEqual(status, 0)
        self.assertIn(str(self.folder), err)
        self.assertEqual(out, "")
        self.assertEqual(snapshot(self.root), before)
