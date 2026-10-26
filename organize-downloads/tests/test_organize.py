"""Tests of Organize planner: which entries directly in the organized folder are to be moved, each
with its type folder, and that working this out changes nothing.

organize.plan_moves(folder) gives back one move for each file to be moved, each with the file's
`name` and its `type_folder`; the tests compare these as (name, type_folder) pairs, as the order
of the moves is the listing's to set.
"""

import os
import random
import tempfile
import unittest
from pathlib import Path

from organize_downloads import organize
from tests import DOWNLOADING_ENDINGS, expected_type_folder, last_extension, make_files, snapshot

# Inputs a property test once failed on, each kept so it is checked on every run.
# Append each failing folder content a property test reports here, as the dict it printed.
FAILED_CONTENTS = []


def planned(folder: Path) -> list:
    """Take in a folder; give back the (name, type_folder) pairs the planner plans for it, sorted."""
    return sorted((move.name, move.type_folder) for move in organize.plan_moves(folder))


class OrganizeTestCase(unittest.TestCase):
    """A test with its own empty organized folder, removed after it."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)


class PlanMovesTest(OrganizeTestCase):
    def test_each_plain_file_is_planned_to_the_folder_of_its_last_extension(self):
        # Given: one plain file for each type folder, Others included, one with no extension
        make_files(
            self.folder,
            [
                "holiday.JPG",
                "invoice.pdf",
                "report.tar.gz",
                "song.mp3",
                "clip.mov",
                "Docker.dmg",
                "script.py",
                "Makefile",
            ],
        )
        # When: the moves are planned
        result = planned(self.folder)
        # Then: each file is planned to the folder AC3 gives its last extension
        self.assertEqual(
            result,
            [
                ("Docker.dmg", "Installers"),
                ("Makefile", "Others"),
                ("clip.mov", "Video"),
                ("holiday.JPG", "Images"),
                ("invoice.pdf", "Documents"),
                ("report.tar.gz", "Archives"),
                ("script.py", "Others"),
                ("song.mp3", "Audio"),
            ],
        )

    def test_an_empty_folder_plans_no_move(self):
        # Given: an organized folder with nothing in it
        # When: the moves are planned
        result = planned(self.folder)
        # Then: no move is planned
        self.assertEqual(result, [])

    def test_folders_and_what_is_inside_them_are_not_planned(self):
        # Given: a type folder holding a file, a folder named like a file, and a project folder
        # holding a file, beside one plain file
        (self.folder / "Images").mkdir()
        make_files(self.folder / "Images", ["old.png"])
        (self.folder / "photos.zip").mkdir()
        (self.folder / "Projects").mkdir()
        make_files(self.folder / "Projects", ["plan.pdf"])
        make_files(self.folder, ["invoice.pdf"])
        # When: the moves are planned
        result = planned(self.folder)
        # Then: only the plain file is planned; no folder, nor any file inside one
        self.assertEqual(result, [("invoice.pdf", "Documents")])

    def test_hidden_files_are_not_planned(self):
        # Given: hidden files, macOS's among them and one with a listed extension, beside one
        # plain file
        make_files(self.folder, [".DS_Store", ".localized", ".hidden.jpg", "invoice.pdf"])
        # When: the moves are planned
        result = planned(self.folder)
        # Then: only the plain file that is not hidden is planned
        self.assertEqual(result, [("invoice.pdf", "Documents")])

    def test_files_still_being_downloaded_are_not_planned(self):
        # Given: files still being downloaded by Chrome, Firefox and Safari, their endings in
        # either case, beside one plain file
        make_files(
            self.folder,
            [
                "report.pdf.crdownload",
                "video.mp4.part",
                "setup.dmg.download",
                "slides.pdf.PART",
                "invoice.pdf",
            ],
        )
        # When: the moves are planned
        result = planned(self.folder)
        # Then: only the finished file is planned
        self.assertEqual(result, [("invoice.pdf", "Documents")])

    def test_symbolic_links_are_not_planned_whatever_they_point_to(self):
        # Given: a symbolic link to a file, one to a folder and one to nothing, beside the file
        # and folder they point to
        make_files(self.folder, ["invoice.pdf"])
        (self.folder / "Projects").mkdir()
        os.symlink("invoice.pdf", self.folder / "link-to-file.pdf")
        os.symlink("Projects", self.folder / "link-to-folder.zip")
        os.symlink("missing.jpg", self.folder / "link-to-nothing.jpg")
        # When: the moves are planned
        result = planned(self.folder)
        # Then: only the plain file is planned, no link
        self.assertEqual(result, [("invoice.pdf", "Documents")])

    def test_entries_neither_a_plain_file_nor_a_folder_are_not_planned(self):
        # Given: a named pipe with a listed extension, beside one plain file
        os.mkfifo(self.folder / "stream.mp3")
        make_files(self.folder, ["invoice.pdf"])
        # When: the moves are planned
        result = planned(self.folder)
        # Then: only the plain file is planned
        self.assertEqual(result, [("invoice.pdf", "Documents")])

    def test_planning_changes_nothing_in_the_folder(self):
        # Given: an organized folder holding every kind of entry the planner meets
        make_files(self.folder, ["invoice.pdf", ".DS_Store", "video.mp4.part", "Makefile"])
        (self.folder / "Images").mkdir()
        make_files(self.folder / "Images", ["old.png"])
        os.symlink("invoice.pdf", self.folder / "link.pdf")
        os.mkfifo(self.folder / "stream.mp3")
        before = snapshot(self.folder)
        # When: the moves are planned
        organize.plan_moves(self.folder)
        # Then: every entry is as it was, and none was added
        self.assertEqual(snapshot(self.folder), before)

    def test_any_folder_content_plans_exactly_its_visible_finished_plain_files(self):
        # Property: for many random folder contents, made anew on each run, of plain files,
        # hidden files, files still downloading, folders and symbolic links, under names with
        # random extensions, the planner plans exactly the plain files that are neither hidden
        # nor still downloading, each to the folder of its last extension.
        rng = random.Random()
        extensions = ["jpg", "PDF", "gz", "Mp3", "mov", "dmg", "py", "part", "CRDOWNLOAD", ""]
        kinds = ["file", "hidden", "folder", "link"]
        contents = list(FAILED_CONTENTS)
        for _ in range(50):
            content = {}
            for number in range(rng.randrange(8)):
                extension = rng.choice(extensions)
                name = f"entry{number}" + (f".{extension}" if extension else "")
                kind = rng.choice(kinds)
                content["." + name if kind == "hidden" else name] = kind
            contents.append(content)
        for content in contents:
            with self.subTest(content=content):
                # Given: an organized folder of that content
                with tempfile.TemporaryDirectory() as temporary:
                    folder = Path(temporary)
                    for name, kind in content.items():
                        if kind == "folder":
                            (folder / name).mkdir()
                        elif kind == "link":
                            os.symlink(".", folder / name)
                        else:
                            make_files(folder, [name])
                    expected = sorted(
                        (name, expected_type_folder(name))
                        for name, kind in content.items()
                        if kind == "file" and last_extension(name) not in DOWNLOADING_ENDINGS
                    )
                    # When: the moves are planned
                    result = planned(folder)
                # Then: exactly its visible, finished plain files are planned to their folders
                self.assertEqual(result, expected)
