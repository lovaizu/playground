"""Tests of Type table: which type folder a file's name sends it to, and which names are files
still being downloaded.

The expected folders and endings are those tests/__init__.py writes from AC3 and AC5 of the
requirements, not taken from the module, so a test fails when the module's table drifts from what
the user settled.
"""

import random
import string
import unittest

from organize_downloads import type_table
from tests import DOWNLOADING_ENDINGS, FOLDER_BY_EXTENSION, expected_type_folder, last_extension

# Characters a random file name is made of: every printable ASCII character and every ASCII
# whitespace, line breaks and tab included, and a few letters beyond ASCII; left out are "/" and
# NUL, which no file name holds, other control characters, and "." which the tests place
# themselves to set the extension.
NAME_CHARACTERS = "".join(char for char in string.printable if char not in "/.") + "äöéあダ文"

# Inputs a property test once failed on, each kept so it is checked on every run.
# Append each failing input a property test reports here, as the name it printed.
FAILED_NAMES = []


def random_case(rng: random.Random, text: str) -> str:
    """Take in a random source and a text; give back the text with each letter's case drawn at random."""
    return "".join(rng.choice([char.lower(), char.upper()]) for char in text)


def random_stem(rng: random.Random) -> str:
    """Take in a random source; give back a file name's start of 1 to 12 characters, which may
    hold dots of its own but never begins with one."""
    stem = rng.choice(NAME_CHARACTERS)
    for _ in range(rng.randrange(12)):
        stem += rng.choice(NAME_CHARACTERS + ".")
    return stem


class TypeFolderForTest(unittest.TestCase):
    """type_table.type_folder_for(name) gives the type folder a file of that name goes to."""

    def test_each_extension_of_ac3_sends_a_file_to_its_folder(self):
        for extension, folder in FOLDER_BY_EXTENSION.items():
            with self.subTest(extension=extension):
                # Given: a file whose name ends with one of AC3's extensions
                name = f"file.{extension}"
                # When: its type folder is asked for
                result = type_table.type_folder_for(name)
                # Then: it is the folder AC3 gives that extension
                self.assertEqual(result, folder)

    def test_an_extension_matches_whatever_the_case_of_its_letters(self):
        for name, folder in [
            ("photo.JPG", "Images"),
            ("photo.Jpeg", "Images"),
            ("Report.PDF", "Documents"),
            ("setup.AppImage", "Installers"),
            ("clip.MP4", "Video"),
        ]:
            with self.subTest(name=name):
                # Given: a file whose extension has upper-case letters
                # When: its type folder is asked for
                result = type_table.type_folder_for(name)
                # Then: it is the folder of the same extension in lower case
                self.assertEqual(result, folder)

    def test_only_the_last_extension_decides_the_folder(self):
        for name, folder in [
            ("report.tar.gz", "Archives"),
            ("photo.jpg.zip", "Archives"),
            ("backup.zip.pdf", "Documents"),
            ("notes.v2.txt", "Documents"),
        ]:
            with self.subTest(name=name):
                # Given: a file whose name has more than one extension
                # When: its type folder is asked for
                result = type_table.type_folder_for(name)
                # Then: it is the folder of the extension after the last dot
                self.assertEqual(result, folder)

    def test_a_file_with_no_extension_goes_to_others(self):
        for name in ["Makefile", "jpg", "README", "file."]:
            with self.subTest(name=name):
                # Given: a file whose name has no dot, or nothing after its last dot
                # When: its type folder is asked for
                result = type_table.type_folder_for(name)
                # Then: it is Others
                self.assertEqual(result, "Others")

    def test_a_file_whose_extension_is_in_no_folder_goes_to_others(self):
        for name in ["script.py", "photo.jpgx", "photo.jp", "data.json", "movie.mp4.bak"]:
            with self.subTest(name=name):
                # Given: a file whose last extension AC3 names for no folder, one close to a
                # listed extension included
                # When: its type folder is asked for
                result = type_table.type_folder_for(name)
                # Then: it is Others
                self.assertEqual(result, "Others")

    def test_any_name_ending_with_a_listed_extension_goes_to_its_folder(self):
        # Property: for many random names, made anew on each run, with a listed extension in a
        # random case after the last dot, the folder is the one AC3 gives that extension.
        rng = random.Random()
        extensions = sorted(FOLDER_BY_EXTENSION)
        names = FAILED_NAMES + [
            f"{random_stem(rng)}.{random_case(rng, rng.choice(extensions))}" for _ in range(500)
        ]
        for name in names:
            expected = expected_type_folder(name)
            with self.subTest(name=name):
                # Given: a file of a random name
                # When: its type folder is asked for
                result = type_table.type_folder_for(name)
                # Then: it is the folder of its last extension
                self.assertEqual(result, expected)

    def test_any_name_ending_with_an_unlisted_extension_goes_to_others(self):
        # Property: for many random names, made anew on each run, whose last extension AC3 does
        # not list, the folder is Others.
        rng = random.Random()
        names = []
        while len(names) < 500:
            extension = "".join(
                rng.choice(string.ascii_letters + string.digits) for _ in range(rng.randint(1, 6))
            )
            if extension.lower() not in FOLDER_BY_EXTENSION:
                names.append(f"{random_stem(rng)}.{extension}")
        for name in names:
            with self.subTest(name=name):
                # Given: a file of a random name whose last extension is in no folder
                # When: its type folder is asked for
                result = type_table.type_folder_for(name)
                # Then: it is Others
                self.assertEqual(result, "Others")


class IsStillDownloadingTest(unittest.TestCase):
    """type_table.is_still_downloading(name) tells whether a file of that name is still being
    downloaded."""

    def test_a_name_with_a_downloading_ending_is_still_downloading(self):
        for name in ["report.pdf.crdownload", "video.mp4.part", "setup.dmg.download", "x.part"]:
            with self.subTest(name=name):
                # Given: a file whose name ends with an ending AC5 gives a download in progress
                # When: whether it is still being downloaded is asked
                result = type_table.is_still_downloading(name)
                # Then: it is
                self.assertTrue(result)

    def test_a_downloading_ending_matches_whatever_the_case_of_its_letters(self):
        for name in ["report.pdf.PART", "video.CRDOWNLOAD", "setup.dmg.Download"]:
            with self.subTest(name=name):
                # Given: a file whose downloading ending has upper-case letters
                # When: whether it is still being downloaded is asked
                result = type_table.is_still_downloading(name)
                # Then: it is, as the user decided endings match without regard to case
                self.assertTrue(result)

    def test_a_name_without_a_downloading_ending_is_not_still_downloading(self):
        for name in [
            "report.pdf",
            "part",
            "download",
            "video.partial",
            "archive.part.zip",
            "chapter-part",
            "Makefile",
        ]:
            with self.subTest(name=name):
                # Given: a file whose last extension is no downloading ending, though the ending's
                # word may stand elsewhere in its name
                # When: whether it is still being downloaded is asked
                result = type_table.is_still_downloading(name)
                # Then: it is not
                self.assertFalse(result)

    def test_any_name_with_a_downloading_ending_is_still_downloading(self):
        # Property: for many random names, made anew on each run, ending with a downloading
        # ending in a random case, the file is still being downloaded.
        rng = random.Random()
        names = FAILED_NAMES + [
            f"{random_stem(rng)}.{random_case(rng, rng.choice(DOWNLOADING_ENDINGS))}"
            for _ in range(500)
        ]
        for name in names:
            expected = last_extension(name) in DOWNLOADING_ENDINGS
            with self.subTest(name=name):
                # Given: a file of a random name
                # When: whether it is still being downloaded is asked
                result = type_table.is_still_downloading(name)
                # Then: it is exactly when its last extension is a downloading ending
                self.assertEqual(result, expected)
