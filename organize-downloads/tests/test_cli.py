"""Tests of Command line: what the run with nothing added prints, which folder it organizes, and
that it changes nothing.

Each test calls cli.main with the arguments the user would type after organize-downloads and
reads what it prints and the exit status it gives back. The test with no folder given sets HOME to
a temporary home that names its Downloads both the macOS and the Linux way, so it holds on either
system and never reads the user's own home.
"""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from organize_downloads import cli
from tests import listed_moves, make_files, make_home, snapshot


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

    def test_a_run_with_nothing_to_move_lists_no_file(self):
        # Given: a folder holding only a folder and a hidden file
        (self.root / "Projects").mkdir()
        make_files(self.root, [".DS_Store"])
        # When: the command runs with that folder given last
        status, output, _ = run_main([str(self.root)])
        # Then: it ends well and lists no file
        self.assertEqual(status, 0)
        self.assertEqual(listed_moves(output), [])

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
