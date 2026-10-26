"""Tests of Command line: what the run with nothing added prints, which folder it organizes, that
it changes nothing, what the run with --apply moves and prints, how it prints names, and why it
stops.

Each test calls cli.main with the arguments the user would type after organize-downloads and
reads what it prints and the exit status it gives back, the planner, os.link or the system's name
replaced only where a test says why. The tests with no folder given set HOME to a temporary home
that names its Downloads both the macOS and the Linux way, so they hold on either system and never
read the user's own home.
"""

import contextlib
import errno
import io
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from organize_downloads import cli, organize
from tests import (
    EXTENSIONS_BY_FOLDER,
    NAME_TAKEN_HEADING_END,
    NO_HARD_LINKS,
    RECORD_NAME,
    WRITE_FAILED,
    after_moves,
    link_failing_for_name,
    link_failing_on_second_call,
    listed_moves,
    make_files,
    make_home,
    snapshot,
    snapshot_without_record,
    stand_in_for_os,
    write_user_dirs,
)

# The error of a disk that is full, as the record's write meets it.
DISK_FULL = OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))


def run_main(arguments: list) -> tuple:
    """Take in the arguments typed after organize-downloads; run cli.main on them and give back
    (exit status, what it printed to standard output, what it printed to standard error)."""
    output = io.StringIO()
    errors = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        status = cli.main(arguments)
    return status, output.getvalue(), errors.getvalue()


class CommandLineTestCase(unittest.TestCase):
    """A test with its own empty temporary folder, removed after it."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)


class ListingRunTest(CommandLineTestCase):
    def test_a_run_with_a_folder_given_lists_each_file_with_its_type_folder(self):
        # Given: a folder holding a photo, an invoice, an installer and a file of no listed type
        make_files(self.root, ["holiday.jpg", "invoice.pdf", "Docker.dmg", "script.py"])
        # When: the command runs with that folder given last
        status, output, _ = run_main([str(self.root)])
        # Then: it ends well and lists each file once, with its type folder
        self.assertEqual(status, 0)
        self.assertEqual(
            sorted(listed_moves(output)),
            [
                ("Docker.dmg", "Installers"),
                ("holiday.jpg", "Images"),
                ("invoice.pdf", "Documents"),
                ("script.py", "Others"),
            ],
        )

    def test_a_run_lists_no_folder_link_hidden_file_or_unfinished_download(self):
        # Given: a folder holding a type folder, a project folder, a symbolic link, hidden files
        # and files still downloading, beside one plain file
        (self.root / "Images").mkdir()
        (self.root / "Projects").mkdir()
        make_files(self.root / "Projects", ["plan.pdf"])
        make_files(
            self.root,
            [".DS_Store", ".localized", "report.pdf.crdownload", "video.mp4.PART", "invoice.pdf"],
        )
        os.symlink("invoice.pdf", self.root / "shortcut.pdf")
        # When: the command runs with that folder given last
        status, output, _ = run_main([str(self.root)])
        # Then: only the plain file is listed, and no other entry's name is printed
        self.assertEqual(status, 0)
        self.assertEqual(listed_moves(output), [("invoice.pdf", "Documents")])
        for name in [
            "Projects",
            "plan.pdf",
            ".DS_Store",
            ".localized",
            "report.pdf.crdownload",
            "video.mp4.PART",
            "shortcut.pdf",
        ]:
            self.assertNotIn(name, output)

    def test_a_run_with_nothing_to_move_says_so_and_lists_no_file(self):
        # Given: a folder holding only a folder and a hidden file
        (self.root / "Projects").mkdir()
        make_files(self.root, [".DS_Store"])
        # When: the command runs with that folder given last
        status, output, _ = run_main([str(self.root)])
        # Then: it ends well and says there is no file to move in that folder, and nothing else
        self.assertEqual(status, 0)
        self.assertEqual(output, f"No file to move in {self.root}.\n")

    def test_a_listing_shows_the_count_each_move_lined_up_by_name_and_that_nothing_moved(self):
        # Given: a folder holding a photo, an invoice and an installer, as in the README's Example
        make_files(self.root, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        # When: the command runs with that folder given last
        status, output, _ = run_main([str(self.root)])
        # Then: it prints how many files would move and where, one line for each sorted by name,
        # the arrows lined up two spaces after the longest name, and that nothing was moved
        self.assertEqual(status, 0)
        self.assertEqual(
            output,
            f"Would move 3 files in {self.root}:\n"
            "  Docker.dmg   -> Installers/\n"
            "  holiday.jpg  -> Images/\n"
            "  invoice.pdf  -> Documents/\n"
            "Nothing was moved.\n",
        )

    def test_a_listing_of_one_file_says_file_not_files(self):
        # Given: a folder holding one file
        make_files(self.root, ["invoice.pdf"])
        # When: the command runs with that folder given last
        status, output, _ = run_main([str(self.root)])
        # Then: the heading counts it as 1 file
        self.assertEqual(status, 0)
        self.assertEqual(output.splitlines()[0], f"Would move 1 file in {self.root}:")

    def test_a_listing_run_changes_nothing_in_the_folder(self):
        # Given: a folder holding files of several types, a type folder and a hidden file
        make_files(self.root, ["holiday.jpg", "invoice.pdf", ".DS_Store", "video.mp4.part"])
        (self.root / "Documents").mkdir()
        make_files(self.root / "Documents", ["old.pdf"])
        before = snapshot(self.root)
        # When: the command runs with that folder given last
        run_main([str(self.root)])
        # Then: every file and folder is as it was, and nothing was added, a record file included
        self.assertEqual(snapshot(self.root), before)

    def test_a_run_with_no_folder_given_lists_the_downloads_folder(self):
        # Given: a home whose Downloads, named the macOS way and in user-dirs settings the Linux
        # way, holds an invoice, beside a photo in home itself
        home = self.root
        make_files(make_home(home), ["invoice.pdf"])
        make_files(home, ["holiday.jpg"])
        before = snapshot(home)
        # When: the command runs with nothing added, HOME being that home
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            os.environ.pop("XDG_CONFIG_HOME", None)
            status, output, _ = run_main([])
        # Then: it lists the file in Downloads alone, and changes nothing in home
        self.assertEqual(status, 0)
        self.assertEqual(listed_moves(output), [("invoice.pdf", "Documents")])
        self.assertEqual(snapshot(home), before)

    def test_a_run_with_no_folder_given_finds_downloads_the_way_of_the_system_named(self):
        # Given: a home whose ~/Downloads, the macOS way, holds one file, and whose user-dirs
        # settings, the Linux way, name another folder holding another file
        home = self.root
        (home / "Downloads").mkdir()
        make_files(home / "Downloads", ["macos.pdf"])
        (home / "Linux downloads").mkdir()
        make_files(home / "Linux downloads", ["linux.pdf"])
        write_user_dirs(home, 'XDG_DOWNLOAD_DIR="$HOME/Linux downloads"\n')
        for system, expected in [("Darwin", "macos.pdf"), ("Linux", "linux.pdf")]:
            with self.subTest(system=system):
                # When: the command runs with nothing added, HOME being that home, on a system
                # that platform.system() names so
                with mock.patch.dict(os.environ, {"HOME": str(home)}), mock.patch(
                    "platform.system", return_value=system
                ):
                    os.environ.pop("XDG_CONFIG_HOME", None)
                    status, output, _ = run_main([])
                # Then: it lists the file of the folder that system's way names
                self.assertEqual(status, 0)
                self.assertEqual(listed_moves(output), [(expected, "Documents")])


class ApplyRunTest(CommandLineTestCase):
    """With --apply, the run hands the moves it lists to Mover and prints each move, and each file
    left in place with why. What a move does to the folder is Mover's, held in test_mover; these
    tests hold that the command makes the moves and what it prints."""

    def test_apply_moves_each_listed_file_into_its_type_folder(self):
        # Given: a folder holding a photo, an invoice and an installer, as in the README's Example
        make_files(self.root, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        before = snapshot(self.root)
        # When: the command runs with --apply and that folder given last
        run_main(["--apply", str(self.root)])
        # Then: each file is in its type folder under the same name, and a record of the moves
        # is in the folder
        self.assertEqual(
            snapshot_without_record(self.root),
            after_moves(
                before,
                "",
                [
                    ("Docker.dmg", "Installers"),
                    ("holiday.jpg", "Images"),
                    ("invoice.pdf", "Documents"),
                ],
            ),
        )
        self.assertTrue((self.root / RECORD_NAME).is_file())

    def test_apply_prints_how_many_files_moved_and_each_move_lined_up(self):
        # Given: a folder holding a photo, an invoice and an installer, as in the README's Example
        make_files(self.root, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        # When: the command runs with --apply and that folder given last
        status, output, errors = run_main(["--apply", str(self.root)])
        # Then: it ends well and prints how many files moved and where, one line for each sorted
        # by name, the arrows lined up two spaces after the longest name
        self.assertEqual((status, errors), (0, ""))
        self.assertEqual(
            output,
            f"Moved 3 files in {self.root}:\n"
            "  Docker.dmg   -> Installers/\n"
            "  holiday.jpg  -> Images/\n"
            "  invoice.pdf  -> Documents/\n",
        )

    def test_apply_given_after_the_folder_moves_too_and_counts_1_file(self):
        # Given: a folder holding one file
        make_files(self.root, ["invoice.pdf"])
        # When: the command runs with the folder given first and --apply after it
        status, output, _ = run_main([str(self.root), "--apply"])
        # Then: it ends well, and the heading says 1 file moved
        self.assertEqual(status, 0)
        self.assertEqual(output.splitlines()[0], f"Moved 1 file in {self.root}:")

    def test_a_file_whose_name_is_taken_is_printed_apart_from_the_moved_saying_why(self):
        # Given: a folder holding an installer and an invoice, whose Documents folder already
        # holds a file named invoice.pdf
        make_files(self.root, ["Docker.dmg", "invoice.pdf"])
        (self.root / "Documents").mkdir()
        (self.root / "Documents" / "invoice.pdf").write_text("filed before", encoding="utf-8")
        # When: the command runs with --apply and that folder given last
        status, output, errors = run_main(["--apply", str(self.root)])
        # Then: it ends well and prints the move, then the invoice under a heading saying why it
        # was left, the arrows of both lined up
        self.assertEqual((status, errors), (0, ""))
        self.assertEqual(
            output,
            f"Moved 1 file in {self.root}:\n"
            "  Docker.dmg   -> Installers/\n"
            f"Left 1 file {NAME_TAKEN_HEADING_END}\n"
            "  invoice.pdf  -> Documents/\n",
        )

    def test_when_every_name_is_taken_it_says_no_file_moved_and_which_were_left(self):
        # Given: a folder holding two invoices, each name already taken in Documents
        make_files(self.root, ["invoice.pdf", "receipt.pdf"])
        (self.root / "Documents").mkdir()
        make_files(self.root / "Documents", ["invoice.pdf", "receipt.pdf"])
        # When: the command runs with --apply and that folder given last
        status, output, _ = run_main(["--apply", str(self.root)])
        # Then: it ends well, and says no file moved, and which were left and why
        self.assertEqual(status, 0)
        self.assertEqual(
            output,
            f"Moved no file in {self.root}.\n"
            f"Left 2 files {NAME_TAKEN_HEADING_END}\n"
            "  invoice.pdf  -> Documents/\n"
            "  receipt.pdf  -> Documents/\n",
        )

    def test_apply_with_nothing_to_move_says_so(self):
        # Given: a folder holding only a folder and a hidden file
        (self.root / "Projects").mkdir()
        make_files(self.root, [".DS_Store"])
        # When: the command runs with --apply and that folder given last
        status, output, _ = run_main(["--apply", str(self.root)])
        # Then: it ends well and says there is no file to move, as the listing does
        self.assertEqual(status, 0)
        self.assertEqual(output, f"No file to move in {self.root}.\n")

    def test_where_no_hard_link_can_be_made_it_prints_that_no_file_moved_and_each_left(self):
        # Given: a folder holding an installer and an invoice, on a file system that cannot make
        # hard links, such as exFAT, whose every link fails so
        make_files(self.root, ["Docker.dmg", "invoice.pdf"])
        # When: the command runs with --apply and that folder given last
        with stand_in_for_os(link=mock.Mock(side_effect=NO_HARD_LINKS)):
            status, output, _ = run_main(["--apply", str(self.root)])
        # Then: it ends with the status of a stop, and prints that no file moved and that both
        # were left as the run stopped
        self.assertEqual(status, 1)
        self.assertEqual(
            output,
            f"Moved no file in {self.root}.\n"
            "Left 2 files in place, as the run stopped:\n"
            "  Docker.dmg   -> Installers/\n"
            "  invoice.pdf  -> Documents/\n",
        )

    def test_where_no_hard_link_can_be_made_the_stop_names_the_file_and_what_to_check(self):
        # Given: a folder holding an installer and an invoice, on a file system that cannot make
        # hard links, such as exFAT, whose every link fails so
        make_files(self.root, ["Docker.dmg", "invoice.pdf"])
        # When: the command runs with --apply and that folder given last
        with stand_in_for_os(link=mock.Mock(side_effect=NO_HARD_LINKS)):
            _, _, errors = run_main(["--apply", str(self.root)])
        # Then: standard error holds one line naming the file it could not move, the reason,
        # and what to check
        self.assertEqual(
            errors,
            "organize-downloads: cannot move Docker.dmg into Installers/ "
            f"({os.strerror(errno.EPERM)}): check that you may write in {self.root} and that it "
            "is on a file system that can make hard links, which exFAT and FAT32 cannot\n",
        )

    def test_a_stop_midway_prints_the_files_moved_before_it_and_those_left(self):
        # Given: a folder holding three files, the link of the second failing for a reason other
        # than its name being taken
        make_files(self.root, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        # When: the command runs with --apply and that folder given last
        with stand_in_for_os(link=link_failing_on_second_call(WRITE_FAILED)):
            status, output, _ = run_main(["--apply", str(self.root)])
        # Then: it ends with the status of a stop, and prints the one move made and the two
        # files left
        self.assertEqual(status, 1)
        self.assertEqual(
            output,
            f"Moved 1 file in {self.root}:\n"
            "  Docker.dmg   -> Installers/\n"
            "Left 2 files in place, as the run stopped:\n"
            "  holiday.jpg  -> Images/\n"
            "  invoice.pdf  -> Documents/\n",
        )

    def test_a_stop_midway_names_the_file_whose_move_failed(self):
        # Given: a folder holding three files, the link of the second failing for a reason other
        # than its name being taken
        make_files(self.root, ["holiday.jpg", "invoice.pdf", "Docker.dmg"])
        # When: the command runs with --apply and that folder given last
        with stand_in_for_os(link=link_failing_on_second_call(WRITE_FAILED)):
            _, _, errors = run_main(["--apply", str(self.root)])
        # Then: standard error names the second file, whose move failed, and its type folder
        self.assertTrue(
            errors.startswith("organize-downloads: cannot move holiday.jpg into Images/"), errors
        )

    def test_a_name_taken_and_a_stop_in_one_run_are_printed_each_under_its_heading(self):
        # Given: a folder holding an installer, an invoice whose name is taken in Documents, and
        # notes, the link of the notes failing for a reason other than its name
        make_files(self.root, ["Docker.dmg", "invoice.pdf", "notes.txt"])
        (self.root / "Documents").mkdir()
        make_files(self.root / "Documents", ["invoice.pdf"])
        # When: the command runs with --apply and that folder given last
        with stand_in_for_os(link=link_failing_for_name("notes.txt", WRITE_FAILED)):
            status, output, _ = run_main(["--apply", str(self.root)])
        # Then: it ends with the status of a stop and prints the move, then the invoice left for
        # its taken name, then the notes left by the stop, the arrows of all lined up
        self.assertEqual(status, 1)
        self.assertEqual(
            output,
            f"Moved 1 file in {self.root}:\n"
            "  Docker.dmg   -> Installers/\n"
            f"Left 1 file {NAME_TAKEN_HEADING_END}\n"
            "  invoice.pdf  -> Documents/\n"
            "Left 1 file in place, as the run stopped:\n"
            "  notes.txt    -> Documents/\n",
        )

    def test_a_type_folder_name_held_by_a_file_stops_the_run_saying_to_move_it(self):
        # Given: a folder holding an installer, and a plain file named Installers where its
        # type folder would be
        make_files(self.root, ["Docker.dmg", "Installers"])
        # When: the command runs with --apply and that folder given last
        status, _, errors = run_main(["--apply", str(self.root)])
        # Then: it ends with the status of a stop, and standard error holds one line naming the
        # entry that is not a folder and what to do
        self.assertEqual(status, 1)
        self.assertEqual(
            errors,
            "organize-downloads: cannot move Docker.dmg into Installers/, as "
            f"{self.root / 'Installers'} is not a folder: move or rename it, and run again\n",
        )

    def test_a_file_gone_before_its_move_stops_naming_it_and_to_run_again(self):
        # Given: a folder holding an installer and an invoice, the invoice moved away after the
        # moves were worked out, as another run at the same time would
        make_files(self.root, ["Docker.dmg", "invoice.pdf"])
        planned = organize.plan_moves(self.root)
        (self.root / "invoice.pdf").unlink()
        # When: the command runs with --apply and that folder given last
        with mock.patch.object(organize, "plan_moves", return_value=planned):
            status, _, errors = run_main(["--apply", str(self.root)])
        # Then: it ends with the status of a stop, and standard error holds one line naming the
        # file, that it is no longer there, and to run again
        self.assertEqual(status, 1)
        self.assertEqual(
            errors,
            "organize-downloads: cannot move invoice.pdf into Documents/, as it is no longer in "
            f"{self.root}, such as when another run moves it at the same time: run again to move "
            "the files left\n",
        )

    def test_a_record_that_cannot_be_written_prints_the_file_as_left_by_the_stop(self):
        # Given: a folder holding an invoice, on a disk that is full when the record of its move
        # is written
        make_files(self.root, ["invoice.pdf"])
        # When: the command runs with --apply and that folder given last
        with stand_in_for_os(replace=mock.Mock(side_effect=DISK_FULL)):
            status, output, _ = run_main(["--apply", str(self.root)])
        # Then: it ends with the status of a stop, and prints that no file moved and that the
        # invoice, put back, was left as the run stopped
        self.assertEqual(status, 1)
        self.assertEqual(
            output,
            f"Moved no file in {self.root}.\n"
            "Left 1 file in place, as the run stopped:\n"
            "  invoice.pdf  -> Documents/\n",
        )

    def test_a_record_that_cannot_be_written_stops_naming_it_and_what_to_check(self):
        # Given: a folder holding an invoice, on a disk that is full when the record of its move
        # is written
        make_files(self.root, ["invoice.pdf"])
        # When: the command runs with --apply and that folder given last
        with stand_in_for_os(replace=mock.Mock(side_effect=DISK_FULL)):
            _, _, errors = run_main(["--apply", str(self.root)])
        # Then: standard error holds one line naming the record file, the reason, and what to
        # check
        self.assertEqual(
            errors,
            f"organize-downloads: cannot write {self.root / RECORD_NAME}, the record undo reads "
            f"to put files back ({os.strerror(errno.ENOSPC)}): check that you may write in "
            f"{self.root} and that its disk has room, and run again\n",
        )

    def test_a_moved_name_holding_a_line_break_is_printed_on_one_line_escaped(self):
        # Given: a folder holding a file whose name holds a line break
        make_files(self.root, ["line\nbreak.txt"])
        # When: the command runs with --apply and that folder given last
        status, output, _ = run_main(["--apply", str(self.root)])
        # Then: its line shows the line break as \n
        self.assertEqual(status, 0)
        self.assertEqual(listed_moves(output), [("line\\nbreak.txt", "Documents")])


class StopTest(CommandLineTestCase):
    def test_a_given_path_that_is_no_folder_stops_the_run_naming_it(self):
        for name in ["no-such-folder", "notes.txt"]:
            with self.subTest(name=name):
                # Given: a path where there is nothing, or a plain file
                make_files(self.root, ["notes.txt"])
                given = self.root / name
                before = snapshot(self.root)
                # When: the command runs with that path given last
                status, output, errors = run_main([str(given)])
                # Then: it ends with a failing status, names the path on standard error, lists
                # nothing and changes nothing
                self.assertNotEqual(status, 0)
                self.assertIn(str(given), errors)
                self.assertEqual(listed_moves(output), [])
                self.assertEqual(snapshot(self.root), before)

    def test_with_apply_a_given_path_that_is_no_folder_stops_the_run_moving_nothing(self):
        for name in ["no-such-folder", "notes.txt"]:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as temporary:
                    # Given: a path where there is nothing, or a plain file, in a home whose
                    # Downloads, named the macOS and the Linux way, holds a file, so a run that
                    # fell back to Downloads would find it there and not in the user's own home
                    home = Path(temporary)
                    make_files(make_home(home), ["invoice.pdf"])
                    make_files(home, ["notes.txt"])
                    given = home / name
                    before = snapshot(home)
                    # When: the command runs with --apply and that path given last, HOME being
                    # that home
                    with mock.patch.dict(os.environ, {"HOME": str(home)}):
                        os.environ.pop("XDG_CONFIG_HOME", None)
                        status, output, errors = run_main(["--apply", str(given)])
                    after = snapshot(home)
                # Then: it ends with the status of a stop, names the path and how to give a
                # folder on standard error, prints no move, and changes nothing, Downloads
                # included
                self.assertEqual(status, 1)
                self.assertIn(f"{given} ", errors)
                self.assertIn("give the folder to organize last", errors)
                self.assertEqual(listed_moves(output), [])
                self.assertEqual(after, before)

    # A folder whose read permission is taken away is still read by root, so the run cannot be
    # made to stop there; GitHub Actions runs the tests as a user that is not root.
    @unittest.skipIf(os.geteuid() == 0, "root reads a folder whatever its permissions")
    def test_with_apply_a_folder_that_cannot_be_read_stops_the_run_moving_nothing(self):
        # Given: a folder holding a file, whose permissions let no one read it, in a home whose
        # Downloads holds a file, so a run that fell back to Downloads would find it there and
        # not in the user's own home
        make_files(make_home(self.root), ["receipt.pdf"])
        locked = self.root / "Locked"
        locked.mkdir()
        make_files(locked, ["invoice.pdf"])
        locked.chmod(0)
        self.addCleanup(locked.chmod, stat.S_IRWXU)
        # When: the command runs with --apply and that folder given last, HOME being that home
        with mock.patch.dict(os.environ, {"HOME": str(self.root)}):
            os.environ.pop("XDG_CONFIG_HOME", None)
            status, output, errors = run_main(["--apply", str(locked)])
        # Then: it ends with the status of a stop, prints no move, stops as the listing does,
        # naming the folder, the reason and what to do, and moves nothing in it or in Downloads
        self.assertEqual(status, 1)
        self.assertEqual(listed_moves(output), [])
        self.assertTrue(errors.startswith(f"organize-downloads: cannot read {locked} ("), errors)
        locked.chmod(stat.S_IRWXU)
        self.assertEqual(os.listdir(locked), ["invoice.pdf"])
        self.assertEqual(os.listdir(self.root / "Downloads"), ["receipt.pdf"])

    def test_a_folder_stop_names_the_command_and_tells_to_give_a_folder_last(self):
        # Given: a path where there is nothing
        given = self.root / "no-such-folder"
        # When: the command runs with that path given last
        status, _, errors = run_main([str(given)])
        # Then: standard error holds one line: the command's name, the path and its condition,
        # and how to give a folder instead
        self.assertEqual(status, 1)
        self.assertEqual(
            errors,
            f"organize-downloads: {given} does not exist: give the folder to organize last: "
            "organize-downloads <folder>\n",
        )

    # A folder whose read permission is taken away is still read by root, so the run cannot be
    # made to stop there; GitHub Actions runs the tests as a user that is not root.
    @unittest.skipIf(os.geteuid() == 0, "root reads a folder whatever its permissions")
    def test_a_folder_that_cannot_be_read_stops_the_run_naming_it_and_why(self):
        # Given: a folder holding a file, whose permissions let no one read it
        locked = self.root / "Locked"
        locked.mkdir()
        make_files(locked, ["invoice.pdf"])
        locked.chmod(0)
        self.addCleanup(locked.chmod, stat.S_IRWXU)
        # When: the command runs with that folder given last
        status, output, errors = run_main([str(locked)])
        # Then: it ends with the status of a stop and lists nothing, and standard error holds
        # one line naming the folder, the reason, and what to do
        self.assertEqual(status, 1)
        self.assertEqual(listed_moves(output), [])
        self.assertEqual(
            errors,
            f"organize-downloads: cannot read {locked} ({os.strerror(errno.EACCES)}): check "
            "that you may read it, or give another folder last\n",
        )


class ShownNameTest(CommandLineTestCase):
    """Names are printed each on one line, as they can be read: a character that cannot be
    printed is written as its escape, and every other character as it is."""

    def test_a_name_holding_a_line_break_or_a_tab_is_listed_on_one_line_escaped(self):
        # Given: a folder holding files whose names hold a line break and a tab
        make_files(self.root, ["line\nbreak.txt", "tab\there.pdf"])
        # When: the command runs with that folder given last
        status, output, _ = run_main([str(self.root)])
        # Then: each name is listed on one line, the line break as \n and the tab as \t
        self.assertEqual(status, 0)
        self.assertEqual(
            sorted(listed_moves(output)),
            [("line\\nbreak.txt", "Documents"), ("tab\\there.pdf", "Documents")],
        )

    def test_a_name_holding_bytes_not_valid_in_the_system_encoding_is_listed_escaped(self):
        # Given: a file whose name holds the byte 0xff, which no UTF-8 text holds, as the planner
        # hands it from a folder on Linux; the name is handed in place of the planner, as macOS's
        # file system refuses to make such a file
        planned = [organize.Move(os.fsdecode(b"bad\xff.pdf"), "Documents")]
        # When: the command lists that file
        with mock.patch.object(organize, "plan_moves", return_value=planned):
            status, output, _ = run_main([str(self.root)])
        # Then: the byte is written as \xff and the rest of the name as it is
        self.assertEqual(status, 0)
        self.assertEqual(listed_moves(output), [("bad\\xff.pdf", "Documents")])

    def test_a_name_beyond_ascii_is_listed_as_it_is(self):
        # Given: a folder holding files whose names hold letters beyond ASCII
        make_files(self.root, ["ダウンロード.pdf", "café.jpg"])
        # When: the command runs with that folder given last
        status, output, _ = run_main([str(self.root)])
        # Then: each name is listed as it is, nothing escaped
        self.assertEqual(status, 0)
        self.assertEqual(
            sorted(listed_moves(output)), [("café.jpg", "Images"), ("ダウンロード.pdf", "Documents")]
        )

    def test_a_folder_name_holding_a_line_break_is_shown_escaped_in_the_listing_heading(self):
        # Given: a folder whose name holds a line break, holding one file
        given = self.root / "new\nfolder"
        given.mkdir()
        make_files(given, ["invoice.pdf"])
        # When: the command runs with that folder given last
        status, output, _ = run_main([str(given)])
        # Then: the heading names the folder on one line, the line break as \n
        self.assertEqual(status, 0)
        self.assertIn(f"Would move 1 file in {self.root}/new\\nfolder:\n", output)

    def test_a_path_name_holding_a_line_break_is_shown_escaped_in_a_stop(self):
        # Given: a path whose name holds a line break, with nothing there
        missing = self.root / "gone\nfolder"
        # When: the command runs with that path given last
        status, _, errors = run_main([str(missing)])
        # Then: the stop is one line on standard error, naming the path with the line break as \n
        self.assertEqual(status, 1)
        self.assertEqual(len(errors.splitlines()), 1)
        self.assertIn(f"{self.root}/gone\\nfolder", errors)


# The width --help's own text is wrapped to: the longest line an 80-column terminal shows whole.
HELP_WIDTH = 79


def help_text() -> str:
    """Run the command with --help and give back what it printed; fails the test unless it ends
    with status 0. COLUMNS is set to 80, so the part argparse wraps by the terminal's width is the
    same on every machine."""
    output = io.StringIO()
    with mock.patch.dict(os.environ, {"COLUMNS": "80"}), contextlib.redirect_stdout(output):
        try:
            cli.main(["--help"])
        except SystemExit as exit_:
            if exit_.code != 0:
                raise AssertionError(f"--help ended with status {exit_.code}") from exit_
        else:
            raise AssertionError("--help did not end the run")
    return output.getvalue()


def help_block(text: str, start: str) -> str:
    """Take in the help text and how a block of it starts; give back that block, the lines from
    the one that starts so to the next blank line."""
    return next(block for block in text.split("\n\n") if block.startswith(start))


def in_one_line(block: str) -> str:
    """Take in a block of the help; give back its words joined by single spaces, so its wording
    is compared apart from where its lines break."""
    return " ".join(block.split())


def table_rows(block: str) -> list:
    """Take in the help's type table; give back each row as its lines, a row beginning at each
    line whose type folder name starts right after the two spaces of indent."""
    rows = []
    for line in block.splitlines():
        if line[2] != " ":
            rows.append([])
        rows[-1].append(line)
    return rows


class HelpTest(unittest.TestCase):
    """--help tells what the command does, what --apply adds, which folder it organizes, which
    extension sends a file to which type folder, and what it leaves in place."""

    def test_help_shows_the_usage_under_the_command_name(self):
        # Given: the command
        # When: it runs with --help
        text = help_text()
        # Then: its first line shows how to type the command, under its own name
        self.assertEqual(text.splitlines()[0], "usage: organize-downloads [-h] [--apply] [folder]")

    def test_help_says_what_the_command_lists_and_that_only_apply_moves(self):
        # Given: the command
        # When: it runs with --help
        text = help_text()
        # Then: the description says it lists where each file would go, and moves only with
        # --apply
        self.assertEqual(
            in_one_line(help_block(text, "List ")),
            "List the type folder each file in your Downloads folder, or in the folder given, "
            "would be moved to. Nothing is moved unless --apply is given.",
        )

    def test_help_says_what_apply_does_and_what_it_leaves(self):
        # Given: the command
        # When: it runs with --help
        text = help_text()
        # Then: the options say --apply moves each file listed, making a missing type folder,
        # and leaves a file whose name is taken in its type folder
        self.assertEqual(
            in_one_line(help_block(text, "options:")),
            "options: -h, --help show this help message and exit --apply move each file listed "
            "into its type folder, making the folder where it is missing; a file whose name is "
            "already taken there is left where it is",
        )

    def test_help_says_which_folder_is_organized_with_none_given(self):
        # Given: the command
        # When: it runs with --help
        text = help_text()
        # Then: the folder argument says what it is, and which folder each system's run takes
        # with none given
        self.assertEqual(
            in_one_line(help_block(text, "positional arguments:")),
            "positional arguments: folder the folder to organize; with none given, ~/Downloads "
            "on macOS, and on Linux the download folder xdg-user-dirs' settings, "
            "~/.config/user-dirs.dirs, name",
        )

    def test_help_says_a_file_goes_by_its_last_extension_in_any_case(self):
        # Given: the command
        # When: it runs with --help
        text = help_text()
        # Then: the sentence before the table says how a file's type folder is found
        self.assertEqual(
            in_one_line(help_block(text, "Each file")),
            "Each file directly in the folder goes to the type folder of its last extension, "
            "matched without regard to case (report.tar.gz goes by gz):",
        )

    def test_help_lists_each_type_folder_with_its_extensions_in_order(self):
        # Given: the command
        # When: it runs with --help
        rows = table_rows(help_block(help_text(), "  Images"))
        # Then: the table lists each type folder of AC3, in its order, with exactly its
        # extensions, then Others
        listed = {row[0].split()[0]: " ".join(" ".join(row).split()[1:]) for row in rows}
        self.assertEqual(
            list(listed), list(EXTENSIONS_BY_FOLDER) + ["Others"], "type folders or their order"
        )
        for type_folder, extensions in EXTENSIONS_BY_FOLDER.items():
            with self.subTest(type_folder=type_folder):
                self.assertEqual(listed[type_folder], extensions)
        self.assertEqual(listed["Others"], "every other file, one with no extension included")

    def test_help_says_which_entries_are_left_in_place(self):
        # Given: the command
        # When: it runs with --help
        text = help_text()
        # Then: it names each kind of entry AC5 leaves in place, and the downloading endings
        self.assertEqual(
            in_one_line(help_block(text, "Left where")),
            "Left where they are and not listed: folders and what is inside them, symbolic "
            "links, other entries that are not plain files, hidden files (whose names begin "
            "with a dot), and files still being downloaded (ending in .crdownload, .part or "
            ".download, in any case).",
        )

    def test_help_table_extensions_start_two_spaces_after_the_longest_folder_name(self):
        # Given: the command
        # When: it runs with --help
        rows = table_rows(help_block(help_text(), "  Images"))
        # Then: on every line of the table the extensions start in one column, two spaces after
        # the longest type folder name, Installers
        column = len("  Installers  ")
        for row in rows:
            name = row[0].split()[0]
            for line, before in zip(row, [f"  {name}"] + [""] * (len(row) - 1)):
                with self.subTest(line=line):
                    self.assertEqual(line[:column], before.ljust(column))
                    self.assertNotEqual(line[column], " ")

    def test_help_text_is_wrapped_to_79_columns(self):
        # Given: the command
        # When: it runs with --help
        text = help_text()
        # Then: in the description, the epilog's sentences and each row of the table, no line
        # is longer than 79 characters, and each line's next word would not have fit on it
        rows = table_rows(help_block(text, "  Images"))
        sentences = [help_block(text, start) for start in ["List ", "Each file", "Left where"]]
        for lines in [block.splitlines() for block in sentences] + rows:
            for line, following in zip(lines, lines[1:] + [None]):
                with self.subTest(line=line):
                    self.assertLessEqual(len(line), HELP_WIDTH)
                    if following is not None:
                        self.assertGreater(len(line) + 1 + len(following.split()[0]), HELP_WIDTH)
