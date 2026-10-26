"""Tests of Mover: moving each planned file into its type folder inside the organized folder under
the same name, overwriting, renaming and deleting nothing, writing each move to Run record, and
handing back the files it did not move.

mover.apply_moves(folder, moves) takes the organized folder and the moves organize.plan_moves gives
for it, and gives back a mover.MoveReport of four fields: `moved`, the moves made, in order;
`name_taken`, the moves left undone because a file of the same name is already in the type folder;
`stopped`, the OSError that stopped the run, None where none did; and `unmoved`, the move that
failed for that reason and each one after it, all left undone.

Mover gives each file its new name as a hard link and then removes the old one, as the
architecture sets; the tests that need a link to fail stand in for os.link with stand_in_for_os,
which reaches Path.hardlink_to too, so Mover may make the link either way. Those that need the old
name's removal or the record's write to fail stand in for os.unlink and os.replace the same way.
"""

import errno
import os
import random
import stat
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from organize_downloads import mover, organize, record
from tests import (
    NO_HARD_LINKS,
    WRITE_FAILED,
    after_moves,
    expected_type_folder,
    link_failing_for_name,
    link_failing_on_second_call,
    make_files,
    move_pairs,
    snapshot,
    snapshot_without_record,
    stand_in_for_os,
)

# Inputs a property test once failed on, each kept so it is checked on every run.
# Append each failing folder content a property test reports here, as the dict it printed.
FAILED_CONTENTS = []


def take_invoice_name(folder: Path, kind: str) -> None:
    """Take in an organized folder and a kind of entry, "file", "folder" or "link to
    nothing"; make an entry of that kind named invoice.pdf in the folder's Documents, making
    Documents. Stops with OSError if it cannot be made."""
    (folder / "Documents").mkdir()
    taken = folder / "Documents" / "invoice.pdf"
    if kind == "file":
        taken.write_text("the invoice already filed", encoding="utf-8")
    elif kind == "folder":
        taken.mkdir()
    else:
        os.symlink("missing.pdf", taken)


# The error of removing a name in a folder that cannot be written.
PERMISSION_DENIED = OSError(errno.EACCES, os.strerror(errno.EACCES))

# The error of a disk that is full, as the record's write meets it.
DISK_FULL = OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))


def unlink_failing_in(folder: Path, error: BaseException) -> Callable[..., None]:
    """Take in a folder and an error; give back a stand-in for os.unlink that removes as os.unlink
    does, but raises the error instead where the name to remove is directly in that folder, as
    removing a file's old name in an organized folder that cannot be written meets."""
    real_unlink = os.unlink

    def unlink(path: os.PathLike | str, *arguments, **keywords) -> None:
        if Path(path).parent == folder:
            raise error
        real_unlink(path, *arguments, **keywords)

    return unlink


def link_failing_into(folder: Path, error: BaseException) -> Callable[..., None]:
    """Take in a folder and an error; give back a stand-in for os.link that links as os.link does,
    but raises the error instead where the new name is directly in that folder, as giving a moved
    file back its old name meets once a file of that name came there."""
    real_link = os.link

    def link(
        source: os.PathLike | str, destination: os.PathLike | str, *arguments, **keywords
    ) -> None:
        if Path(destination).parent == folder:
            raise error
        real_link(source, destination, *arguments, **keywords)

    return link


def replace_failing_on_second_call(error: BaseException) -> Callable[..., None]:
    """Take in an error; give back a stand-in for os.replace that renames as os.replace does on
    every call but the second, which raises the error instead, as a record's write in a run whose
    disk fills up after its first move meets."""
    real_replace = os.replace
    calls = []

    def replace(*arguments, **keywords) -> None:
        calls.append(arguments)
        if len(calls) == 2:
            raise error
        real_replace(*arguments, **keywords)

    return replace


class MoverTestCase(unittest.TestCase):
    """A test with a temporary root holding an organized folder, Downloads, and beside it a file
    and a folder of their own, so a test can check that nothing outside the organized folder
    changes. All is removed after it."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.folder = self.root / "Downloads"
        self.folder.mkdir()
        make_files(self.root, ["outside.jpg"])
        (self.root / "Desktop").mkdir()
        make_files(self.root / "Desktop", ["notes.txt"])

    def assertAllLeftInPlace(self, report: mover.MoveReport, plan: list[organize.Move]) -> None:
        """Fail unless the report says the run stopped before any move, with every move left."""
        self.assertEqual(report.moved, [])
        self.assertEqual(report.name_taken, [])
        self.assertIsNotNone(report.stopped)
        self.assertEqual(move_pairs(report.unmoved), move_pairs(plan))


class MoveTest(MoverTestCase):
    """Each file is moved into its type folder, the folder made where it is missing."""

    def test_each_file_is_moved_into_its_type_folder_under_the_same_name(self):
        # Given: an organized folder holding a photo, an invoice and an installer, none of their
        # type folders there
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        before = snapshot(self.root)
        # When: the moves are applied
        mover.apply_moves(self.folder, plan)
        # Then: each file is in its type folder, made for it, under the same name with the same
        # content and modified time, and nothing else is changed inside or outside the organized
        # folder
        self.assertEqual(
            snapshot_without_record(self.root, "Downloads"),
            after_moves(
                before,
                "Downloads",
                [
                    ("Docker.dmg", "Installers"),
                    ("holiday.jpg", "Images"),
                    ("invoice.pdf", "Documents"),
                ],
            ),
        )

    def test_a_run_with_every_move_made_reports_each_as_moved_and_none_left(self):
        # Given: an organized folder holding a photo, an invoice and an installer
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        report = mover.apply_moves(self.folder, plan)
        # Then: the report names every move as made, in order, none left and no stop
        self.assertEqual(move_pairs(report.moved), move_pairs(plan))
        self.assertEqual((report.name_taken, report.stopped, report.unmoved), ([], None, []))

    def test_a_file_goes_into_its_type_folder_already_there_beside_the_files_in_it(self):
        # Given: an organized folder holding an invoice, and a Documents folder already holding
        # another document
        make_files(self.folder, ["invoice.pdf"])
        (self.folder / "Documents").mkdir()
        make_files(self.folder / "Documents", ["old.pdf"])
        plan = organize.plan_moves(self.folder)
        before = snapshot(self.root)
        # When: the moves are applied
        report = mover.apply_moves(self.folder, plan)
        # Then: the invoice is in Documents beside the document that was there, as it was
        self.assertEqual(
            snapshot_without_record(self.root, "Downloads"),
            after_moves(before, "Downloads", [("invoice.pdf", "Documents")]),
        )
        self.assertEqual(move_pairs(report.moved), [("invoice.pdf", "Documents")])

    def test_no_moves_change_nothing_and_write_no_record(self):
        # Given: an organized folder holding only what the planner leaves in place
        make_files(self.folder, [".DS_Store"])
        (self.folder / "Projects").mkdir()
        before = snapshot(self.root)
        # When: no moves are applied
        report = mover.apply_moves(self.folder, [])
        # Then: nothing is changed, no record file included, and the report names no move
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(report, mover.MoveReport([], [], None, []))


class NameTakenTest(MoverTestCase):
    """A file whose name is already taken in its type folder is left where it is, and the files
    after it are still moved."""

    def test_a_name_taken_in_the_type_folder_leaves_the_file_and_what_took_it(self):
        for kind in ["file", "folder", "link to nothing"]:
            with self.subTest(kind=kind):
                with tempfile.TemporaryDirectory() as temporary:
                    # Given: an organized folder holding an invoice and notes, whose Documents
                    # folder already holds an entry named invoice.pdf of that kind
                    folder = Path(temporary)
                    make_files(folder, ["invoice.pdf", "notes.txt"])
                    take_invoice_name(folder, kind)
                    plan = organize.plan_moves(folder)
                    before = snapshot(folder)
                    # When: the moves are applied
                    mover.apply_moves(folder, plan)
                    # Then: the invoice and the entry that took its name are as they were, and
                    # the notes after it are moved
                    self.assertEqual(
                        snapshot_without_record(folder),
                        after_moves(before, "", [("notes.txt", "Documents")]),
                    )

    def test_a_name_taken_in_the_type_folder_is_reported_apart_from_the_moves_made(self):
        for kind in ["file", "folder", "link to nothing"]:
            with self.subTest(kind=kind):
                with tempfile.TemporaryDirectory() as temporary:
                    # Given: an organized folder holding an invoice and notes, whose Documents
                    # folder already holds an entry named invoice.pdf of that kind
                    folder = Path(temporary)
                    make_files(folder, ["invoice.pdf", "notes.txt"])
                    take_invoice_name(folder, kind)
                    plan = organize.plan_moves(folder)
                    # When: the moves are applied
                    report = mover.apply_moves(folder, plan)
                # Then: the report names the notes as moved and the invoice as left for its
                # taken name, with no stop
                self.assertEqual(move_pairs(report.moved), [("notes.txt", "Documents")])
                self.assertEqual(move_pairs(report.name_taken), [("invoice.pdf", "Documents")])
                self.assertEqual((report.stopped, report.unmoved), (None, []))

    def test_a_name_taken_after_the_moves_were_worked_out_is_not_overwritten(self):
        # Given: moves worked out for an invoice, and then, before they are applied, a file of
        # the same name put in Documents, as a download that just finished would be
        make_files(self.folder, ["invoice.pdf"])
        plan = organize.plan_moves(self.folder)
        take_invoice_name(self.folder, "file")
        before = snapshot(self.root)
        # When: the moves are applied
        mover.apply_moves(self.folder, plan)
        # Then: both files are as they were
        self.assertEqual(snapshot(self.root), before)

    def test_a_name_taken_after_the_moves_were_worked_out_is_reported_as_left(self):
        # Given: moves worked out for an invoice, and then, before they are applied, a file of
        # the same name put in Documents, as a download that just finished would be
        make_files(self.folder, ["invoice.pdf"])
        plan = organize.plan_moves(self.folder)
        take_invoice_name(self.folder, "file")
        # When: the moves are applied
        report = mover.apply_moves(self.folder, plan)
        # Then: the report names the invoice as left for its taken name, and nothing else
        self.assertEqual(move_pairs(report.name_taken), [("invoice.pdf", "Documents")])
        self.assertEqual((report.moved, report.stopped, report.unmoved), ([], None, []))


class StopTest(MoverTestCase):
    """A link that fails for a reason other than the name being taken stops the run there: the
    files after it are not tried, and nothing is undone."""

    def test_where_no_hard_link_can_be_made_the_report_leaves_every_move_with_the_error(self):
        # Given: an organized folder holding a photo, an invoice and an installer, on a file
        # system that cannot make hard links, such as exFAT
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        with stand_in_for_os(link=mock.Mock(side_effect=NO_HARD_LINKS)):
            report = mover.apply_moves(self.folder, plan)
        # Then: the run stops with that error at the first move, every move left
        self.assertAllLeftInPlace(report, plan)
        self.assertEqual(report.stopped.errno, errno.EPERM)

    def test_where_no_hard_link_can_be_made_nothing_is_moved_or_deleted(self):
        # Given: an organized folder holding a photo, an invoice and an installer, on a file
        # system that cannot make hard links, such as exFAT
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        before = snapshot(self.root)
        # When: the moves are applied
        with stand_in_for_os(link=mock.Mock(side_effect=NO_HARD_LINKS)):
            mover.apply_moves(self.folder, plan)
        # Then: every file is where it was, nothing outside is changed, and a type folder made
        # for the moves stays, empty
        after = snapshot(self.root)
        added = {path: entry for path, entry in after.items() if path not in before}
        self.assertEqual({path: after.get(path) for path in before}, before)
        for path, entry in added.items():
            with self.subTest(added=path):
                self.assertEqual(entry, ("folder",))
                self.assertEqual(os.listdir(self.root / path), [])

    def test_a_link_failing_midway_reports_the_moves_made_and_those_left(self):
        # Given: an organized folder holding three files, the second link of which fails for a
        # reason other than its name being taken
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        with stand_in_for_os(link=link_failing_on_second_call(WRITE_FAILED)):
            report = mover.apply_moves(self.folder, plan)
        # Then: the report names the first move as made, and the second and third as left by
        # the stop, with its error
        self.assertEqual(move_pairs(report.moved), [("Docker.dmg", "Installers")])
        self.assertEqual(report.stopped.errno, errno.EIO)
        self.assertEqual(
            move_pairs(report.unmoved), [("holiday.jpg", "Images"), ("invoice.pdf", "Documents")]
        )
        self.assertEqual(report.name_taken, [])

    def test_a_link_failing_midway_keeps_the_moves_made_and_tries_none_after_it(self):
        # Given: an organized folder holding three files, the second link of which fails for a
        # reason other than its name being taken
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        before = snapshot(self.root)
        # When: the moves are applied
        with stand_in_for_os(link=link_failing_on_second_call(WRITE_FAILED)):
            mover.apply_moves(self.folder, plan)
        # Then: the first file is in its type folder, and the second and third are where they
        # were, the third not tried though its link would succeed
        expected = after_moves(before, "Downloads", [("Docker.dmg", "Installers")])
        after = snapshot_without_record(self.root, "Downloads")
        self.assertEqual({path: after.get(path) for path in expected}, expected)

    def test_a_name_taken_before_a_stop_is_reported_apart_from_the_moves_the_stop_left(self):
        # Given: an organized folder holding an installer, an invoice whose name is taken in
        # Documents, and notes, the link of the notes failing for a reason other than its name
        make_files(self.folder, ["Docker.dmg", "invoice.pdf", "notes.txt"])
        (self.folder / "Documents").mkdir()
        make_files(self.folder / "Documents", ["invoice.pdf"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        with stand_in_for_os(link=link_failing_for_name("notes.txt", WRITE_FAILED)):
            report = mover.apply_moves(self.folder, plan)
        # Then: the installer is reported moved, the invoice left for its taken name, and the
        # notes left by the stop
        self.assertEqual(move_pairs(report.moved), [("Docker.dmg", "Installers")])
        self.assertEqual(move_pairs(report.name_taken), [("invoice.pdf", "Documents")])
        self.assertEqual(report.stopped.errno, errno.EIO)
        self.assertEqual(move_pairs(report.unmoved), [("notes.txt", "Documents")])

    def test_a_file_gone_after_the_moves_were_worked_out_stops_the_run_there(self):
        # Given: moves worked out for a photo, an invoice and an installer, and then, before they
        # are applied, the photo moved away, as another run at the same time would
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        (self.folder / "holiday.jpg").rename(self.root / "holiday.jpg")
        # When: the moves are applied
        report = mover.apply_moves(self.folder, plan)
        # Then: the installer before it is moved, and the run stops at the photo, saying it is
        # not there, the invoice after it left
        self.assertEqual(move_pairs(report.moved), [("Docker.dmg", "Installers")])
        self.assertIsInstance(report.stopped, FileNotFoundError)
        self.assertEqual(
            move_pairs(report.unmoved), [("holiday.jpg", "Images"), ("invoice.pdf", "Documents")]
        )

    def test_a_type_folder_name_held_by_something_not_a_folder_stops_the_run(self):
        for kind in ["plain file", "link to a folder outside"]:
            with self.subTest(kind=kind):
                with tempfile.TemporaryDirectory() as temporary:
                    # Given: an organized folder holding an installer, where the name of its type
                    # folder, Installers, is held by a plain file, or by a symbolic link to a
                    # folder outside the organized folder
                    root = Path(temporary)
                    folder = root / "Downloads"
                    folder.mkdir()
                    (root / "Elsewhere").mkdir()
                    make_files(folder, ["Docker.dmg"])
                    if kind == "plain file":
                        make_files(folder, ["Installers"])
                    else:
                        os.symlink(root / "Elsewhere", folder / "Installers")
                    plan = organize.plan_moves(folder)
                    before = snapshot(root)
                    # When: the moves are applied
                    report = mover.apply_moves(folder, plan)
                    # Then: the run stops saying Installers is not a folder, before any move;
                    # nothing inside or outside the organized folder is changed
                    self.assertAllLeftInPlace(report, plan)
                    self.assertIsInstance(report.stopped, NotADirectoryError)
                    self.assertEqual(snapshot(root), before)

    # A folder whose write permission is taken away is still written by root, so the run cannot
    # be made to stop there; GitHub Actions runs the tests as a user that is not root.
    @unittest.skipIf(os.geteuid() == 0, "root writes a folder whatever its permissions")
    def test_an_organized_folder_that_cannot_be_written_stops_the_run_moving_nothing(self):
        # Given: an organized folder holding an invoice, whose permissions let no one write in it
        make_files(self.folder, ["invoice.pdf"])
        plan = organize.plan_moves(self.folder)
        self.folder.chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(self.folder.chmod, stat.S_IRWXU)
        before = snapshot(self.root)
        # When: the moves are applied
        report = mover.apply_moves(self.folder, plan)
        # Then: the run stops with the error that it may not write there, and nothing is changed
        self.assertAllLeftInPlace(report, plan)
        self.assertEqual(report.stopped.errno, errno.EACCES)
        self.assertEqual(snapshot(self.root), before)


class RecordTest(MoverTestCase):
    """Each move made is written to Run record, so undo finds what the last run that moved files
    moved."""

    def test_the_record_holds_each_move_made_in_order(self):
        # Given: an organized folder holding three files, one whose name is taken in its type
        # folder
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        (self.folder / "Images").mkdir()
        make_files(self.folder / "Images", ["holiday.jpg"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        report = mover.apply_moves(self.folder, plan)
        # Then: the record holds the two moves made, in the order made, and not the one left
        self.assertEqual(
            move_pairs(record.read_moves(self.folder)),
            [("Docker.dmg", "Installers"), ("invoice.pdf", "Documents")],
        )
        self.assertEqual(move_pairs(report.moved), move_pairs(record.read_moves(self.folder)))

    def test_a_run_that_moves_files_replaces_the_record_of_the_run_before(self):
        # Given: an organized folder whose record holds a run before, and an invoice to move
        record.write_moves(self.folder, [organize.Move("old.pdf", "Documents")])
        make_files(self.folder, ["invoice.pdf"])
        # When: the moves are applied
        mover.apply_moves(self.folder, organize.plan_moves(self.folder))
        # Then: the record holds this run's move alone
        self.assertEqual(move_pairs(record.read_moves(self.folder)), [("invoice.pdf", "Documents")])

    def test_a_run_that_moves_nothing_leaves_the_record_of_the_run_before(self):
        # Given: an organized folder whose record holds a run before, and an invoice whose name
        # is taken in Documents
        record.write_moves(self.folder, [organize.Move("old.pdf", "Documents")])
        make_files(self.folder, ["invoice.pdf"])
        (self.folder / "Documents").mkdir()
        make_files(self.folder / "Documents", ["invoice.pdf"])
        before = snapshot(self.root)
        # When: the moves are applied, and none is made
        mover.apply_moves(self.folder, organize.plan_moves(self.folder))
        # Then: everything is as it was, the record of the run before included, so undo still
        # puts back that run
        self.assertEqual(snapshot(self.root), before)

    def test_a_run_stopped_midway_keeps_the_moves_made_before_the_stop_in_the_record(self):
        # Given: an organized folder holding three files, the second link of which fails for a
        # reason other than its name being taken
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        with stand_in_for_os(link=link_failing_on_second_call(WRITE_FAILED)):
            mover.apply_moves(self.folder, plan)
        # Then: the record holds the one move made, so undo can put it back
        self.assertEqual(move_pairs(record.read_moves(self.folder)), [("Docker.dmg", "Installers")])

    def test_a_run_ended_by_an_interruption_keeps_each_move_made_in_the_record(self):
        # Given: an organized folder holding three files, the run ended by the user pressing
        # Ctrl-C while the second is moved
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        with stand_in_for_os(link=link_failing_on_second_call(KeyboardInterrupt())):
            with self.assertRaises(KeyboardInterrupt):
                mover.apply_moves(self.folder, plan)
        # Then: the first file is in its type folder and the record names its move, so undo can
        # put it back
        self.assertTrue((self.folder / "Installers" / "Docker.dmg").is_file())
        self.assertFalse(os.path.lexists(self.folder / "Docker.dmg"))
        self.assertIn(("Docker.dmg", "Installers"), move_pairs(record.read_moves(self.folder)))


class UndoneMoveTest(MoverTestCase):
    """A move that fails after its link was made is undone, so its file keeps its old name, the
    run stops there, and nothing is deleted."""

    def test_an_old_name_that_cannot_be_removed_leaves_the_file_as_it_was(self):
        # Given: an organized folder holding an invoice, whose names cannot be removed, as in a
        # folder that cannot be written beside a Documents folder that can
        make_files(self.folder, ["invoice.pdf"])
        plan = organize.plan_moves(self.folder)
        before = snapshot(self.root)
        # When: the moves are applied
        with stand_in_for_os(unlink=unlink_failing_in(self.folder, PERMISSION_DENIED)):
            report = mover.apply_moves(self.folder, plan)
        # Then: the run stops with that error before any move, and the invoice is where it was,
        # its name in Documents removed and no record written; Documents, made for it, stays
        self.assertAllLeftInPlace(report, plan)
        self.assertEqual(report.stopped.errno, errno.EACCES)
        self.assertEqual(snapshot(self.root), {**before, "Downloads/Documents": ("folder",)})

    def test_a_file_whose_two_names_cannot_be_removed_keeps_both(self):
        # Given: an organized folder holding an invoice, where no name can be removed at all
        make_files(self.folder, ["invoice.pdf"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        with stand_in_for_os(unlink=mock.Mock(side_effect=PERMISSION_DENIED)):
            report = mover.apply_moves(self.folder, plan)
        # Then: the run stops before any move, and the invoice has its old name and its name in
        # Documents, the same file, so nothing of it is lost
        self.assertAllLeftInPlace(report, plan)
        self.assertTrue(
            os.path.samefile(self.folder / "invoice.pdf", self.folder / "Documents" / "invoice.pdf")
        )

    def test_a_record_that_cannot_be_written_puts_the_file_back_and_keeps_the_last_record(self):
        # Given: an organized folder whose record holds a run before, and an invoice to move, on a
        # disk that is full when the record is written
        record.write_moves(self.folder, [organize.Move("old.pdf", "Documents")])
        make_files(self.folder, ["invoice.pdf"])
        plan = organize.plan_moves(self.folder)
        before = snapshot(self.root)
        # When: the moves are applied
        with stand_in_for_os(replace=mock.Mock(side_effect=DISK_FULL)):
            report = mover.apply_moves(self.folder, plan)
        # Then: the run stops saying the record was not written, and the invoice is back where it
        # was, so the record of the run before, as it was, still tells undo the last run that
        # moved files; Documents, made for it, stays
        self.assertAllLeftInPlace(report, plan)
        self.assertIsInstance(report.stopped, record.RecordNotWritten)
        self.assertEqual(snapshot(self.root), {**before, "Downloads/Documents": ("folder",)})

    def test_a_record_that_cannot_be_written_midway_keeps_the_moves_before_it(self):
        # Given: an organized folder holding three files, on a disk that is full when the record
        # of the second move is written
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        with stand_in_for_os(replace=replace_failing_on_second_call(DISK_FULL)):
            report = mover.apply_moves(self.folder, plan)
        # Then: the first move is made and in the record, the second file is back where it was
        # and the third not tried, both left by the stop
        self.assertEqual(move_pairs(report.moved), [("Docker.dmg", "Installers")])
        self.assertEqual(
            move_pairs(report.unmoved), [("holiday.jpg", "Images"), ("invoice.pdf", "Documents")]
        )
        self.assertEqual(move_pairs(record.read_moves(self.folder)), [("Docker.dmg", "Installers")])
        self.assertTrue((self.folder / "holiday.jpg").is_file())
        self.assertFalse(os.path.lexists(self.folder / "Images" / "holiday.jpg"))

    def test_a_file_that_cannot_be_put_back_after_the_record_failed_is_reported_moved(self):
        # Given: an organized folder holding three files, on a disk that is full when the record
        # of the second move is written, where no old name can be given back, as when a file of
        # that name came there meanwhile
        make_files(self.folder, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        plan = organize.plan_moves(self.folder)
        # When: the moves are applied
        with stand_in_for_os(
            replace=replace_failing_on_second_call(DISK_FULL),
            link=link_failing_into(self.folder, WRITE_FAILED),
        ):
            report = mover.apply_moves(self.folder, plan)
        # Then: the second file stays in Images, its only place, and is reported moved after the
        # first; the run stops saying the record was not written, and the third is left by it
        self.assertEqual(
            move_pairs(report.moved), [("Docker.dmg", "Installers"), ("holiday.jpg", "Images")]
        )
        self.assertIsInstance(report.stopped, record.RecordNotWritten)
        self.assertEqual(move_pairs(report.unmoved), [("invoice.pdf", "Documents")])
        self.assertTrue((self.folder / "Images" / "holiday.jpg").is_file())
        self.assertFalse(os.path.lexists(self.folder / "holiday.jpg"))


class AnyFolderTest(unittest.TestCase):
    def test_any_folder_content_keeps_every_file_and_folder_under_the_same_name(self):
        # Property: for many random folder contents, made anew on each run, of plain files of
        # random types beside type folders already holding files of random names, some the
        # same, after the moves are applied every file that was in the organized folder or its
        # type folders is still in one of them under the same name with the same content, every
        # folder is still there, each planned file is in its type folder or else named as left
        # for a taken name, and nothing else is changed.
        rng = random.Random()
        names = ["photo.jpg", "invoice.PDF", "backup.tar.gz", "song.mp3", "Makefile", "setup.dmg"]
        type_folders = ["Images", "Documents", "Archives", "Audio", "Others", "Installers"]
        contents = list(FAILED_CONTENTS)
        for _ in range(50):
            contents.append(
                {
                    "files": rng.sample(names, rng.randrange(len(names) + 1)),
                    "filed": {
                        type_folder: rng.sample(names, rng.randrange(3))
                        for type_folder in rng.sample(type_folders, rng.randrange(4))
                    },
                }
            )
        for content in contents:
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as temporary:
                    # Given: an organized folder of that content
                    folder = Path(temporary)
                    make_files(folder, content["files"])
                    for type_folder, filed in content["filed"].items():
                        (folder / type_folder).mkdir()
                        for name in filed:
                            (folder / type_folder / name).write_text(
                                f"filed {name}", encoding="utf-8"
                            )
                    before = snapshot(folder)
                    expected_moves = [
                        (name, expected_type_folder(name))
                        for name in content["files"]
                        if name not in content["filed"].get(expected_type_folder(name), [])
                    ]
                    # When: the moves are applied
                    report = mover.apply_moves(folder, organize.plan_moves(folder))
                    after = snapshot_without_record(folder)
                # Then: exactly the files whose names were free are moved, the others are named
                # as left, and every entry is kept under the same name
                self.assertIsNone(report.stopped)
                self.assertEqual(sorted(move_pairs(report.moved)), sorted(expected_moves))
                self.assertEqual(
                    sorted(move_pairs(report.moved) + move_pairs(report.name_taken)),
                    sorted((name, expected_type_folder(name)) for name in content["files"]),
                )
                self.assertEqual(after, after_moves(before, "", expected_moves))

