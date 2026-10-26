"""Tests of Run record: the hidden file .organize-last-run inside the organized folder that holds
the moves of the last run that moved files, so undo can read them, written so that an interrupted
write leaves the last record whole.

record.write_moves(folder, moves) writes the moves, each an organize.Move, as the folder's record,
in place of the one before; record.read_moves(folder) gives them back in the same order. Run record
writes a new file beside the old and renames it over the old, as the architecture sets; the tests
that watch or interrupt that rename stand in for os.replace and os.rename with stand_in_for_os,
which reaches Path.replace and Path.rename too, so Run record may rename either way, and they make
it fail as a crash or a full disk would between writing the new file and putting it in place.
"""

import contextlib
import errno
import json
import os
import random
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from organize_downloads import organize, record
from tests import (
    EXTENSIONS_BY_FOLDER,
    RECORD_NAME,
    make_files,
    move_pairs,
    snapshot,
    stand_in_for_os,
)

# Characters a random file name is made of: letters, digits and spaces, those JSON writes with a
# backslash (" \ and a line break, a tab), letters beyond ASCII, and a byte no UTF-8 text holds as
# Python gives it for a file name on Linux; "/" and NUL, which no file name holds, are left out.
NAME_CHARACTERS = 'abcXYZ019 .-_"\\\n\täダ文' + os.fsdecode(b"\xff")

# Inputs a property test once failed on, each kept so it is checked on every run.
# Append each failing list of moves a property test reports here, as the list of pairs it printed.
FAILED_MOVES = []


def recording_renames() -> tuple[list[tuple[Path, Path]], contextlib.AbstractContextManager]:
    """Give back a list and a patch that, while active, lets os.replace and os.rename rename as
    they do, and Path's methods that call them, and appends each (source, destination) they are
    called with to the list."""
    renames = []
    real = {"replace": os.replace, "rename": os.rename}

    def wrapper(name: str) -> Callable[..., None]:
        """Take in "replace" or "rename"; give back a stand-in for that os function that appends
        each (source, destination) to the list and then renames as the function does."""

        def rename(
            source: os.PathLike | str, destination: os.PathLike | str, *arguments, **keywords
        ) -> None:
            renames.append((Path(source), Path(destination)))
            real[name](source, destination, *arguments, **keywords)

        return rename

    patch = stand_in_for_os(replace=wrapper("replace"), rename=wrapper("rename"))
    return renames, patch


class RecordTestCase(unittest.TestCase):
    """A test with a temporary root holding an organized folder, Downloads, removed after it."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.folder = self.root / "Downloads"
        self.folder.mkdir()


class WriteAndReadTest(RecordTestCase):
    def test_the_moves_written_are_read_back_in_the_same_order(self):
        # Given: the moves of a run, not in order of name
        moves = [
            organize.Move("invoice.pdf", "Documents"),
            organize.Move("Docker.dmg", "Installers"),
            organize.Move("Makefile", "Others"),
        ]
        # When: they are written as the folder's record and read back
        record.write_moves(self.folder, moves)
        result = record.read_moves(self.folder)
        # Then: the same moves come back, in the order written
        self.assertEqual(move_pairs(result), move_pairs(moves))

    def test_the_record_is_one_hidden_json_file_inside_the_organized_folder(self):
        # Given: an organized folder holding an invoice, beside a file outside it
        make_files(self.folder, ["invoice.pdf"])
        make_files(self.root, ["outside.jpg"])
        before = snapshot(self.root)
        # When: a move is written as the folder's record
        record.write_moves(self.folder, [organize.Move("invoice.pdf", "Documents")])
        # Then: the one entry added, inside the organized folder, is the plain file
        # .organize-last-run, holding JSON
        after = snapshot(self.root)
        self.assertEqual(sorted(set(after) - set(before)), [f"Downloads/{RECORD_NAME}"])
        self.assertEqual({path: after.get(path) for path in before}, before)
        self.assertEqual(after[f"Downloads/{RECORD_NAME}"][0], "file")
        json.loads((self.folder / RECORD_NAME).read_bytes())

    def test_a_write_replaces_the_record_before_it_whole(self):
        # Given: a record of a run of two moves
        record.write_moves(
            self.folder,
            [organize.Move("invoice.pdf", "Documents"), organize.Move("Docker.dmg", "Installers")],
        )
        # When: the moves of a later run, one move, are written
        record.write_moves(self.folder, [organize.Move("holiday.jpg", "Images")])
        # Then: the record holds the later run's move alone
        self.assertEqual(move_pairs(record.read_moves(self.folder)), [("holiday.jpg", "Images")])

    def test_the_record_file_is_left_in_place_by_the_planner(self):
        # Given: an organized folder whose record a run wrote, beside an invoice
        record.write_moves(self.folder, [organize.Move("old.pdf", "Documents")])
        make_files(self.folder, ["invoice.pdf"])
        # When: the moves are planned
        plan = organize.plan_moves(self.folder)
        # Then: the record file, being hidden, is not planned to move
        self.assertEqual(move_pairs(plan), [("invoice.pdf", "Documents")])

    def test_any_moves_written_are_read_back_the_same(self):
        # Property: for many random lists of moves, made anew on each run, of names of random
        # characters, those JSON escapes and bytes no UTF-8 text holds among them, each to a
        # random type folder, what is read back is exactly what was written, in the same order.
        rng = random.Random()
        type_folders = list(EXTENSIONS_BY_FOLDER) + ["Others"]
        lists = list(FAILED_MOVES)
        for _ in range(100):
            lists.append(
                [
                    (
                        "".join(rng.choice(NAME_CHARACTERS) for _ in range(rng.randint(1, 12))),
                        rng.choice(type_folders),
                    )
                    for _ in range(rng.randint(1, 6))
                ]
            )
        for moves in lists:
            with self.subTest(moves=moves):
                # Given: a list of moves of random names
                # When: it is written as the folder's record and read back
                record.write_moves(self.folder, [organize.Move(*move) for move in moves])
                result = record.read_moves(self.folder)
                # Then: the same moves come back, in the same order
                self.assertEqual(move_pairs(result), moves)


class InterruptedWriteTest(RecordTestCase):
    def test_a_write_stopped_before_its_rename_leaves_the_last_record_whole(self):
        # Given: a record of a run, and a disk that fills up while the next record is put in
        # place
        record.write_moves(self.folder, [organize.Move("invoice.pdf", "Documents")])
        written = (self.folder / RECORD_NAME).read_bytes()
        full = OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
        # When: the moves of a later run are written
        failing = {"replace": mock.Mock(side_effect=full), "rename": mock.Mock(side_effect=full)}
        with stand_in_for_os(**failing):
            with self.assertRaises(OSError):
                record.write_moves(self.folder, [organize.Move("holiday.jpg", "Images")])
        # Then: the record file is as it was, so undo still reads the last run's move
        self.assertEqual((self.folder / RECORD_NAME).read_bytes(), written)
        self.assertEqual(move_pairs(record.read_moves(self.folder)), [("invoice.pdf", "Documents")])

    def test_each_write_renames_a_hidden_file_of_its_own_beside_the_record(self):
        # Given: an organized folder
        renames, patch = recording_renames()
        # When: two records are written, as two runs would
        with patch:
            record.write_moves(self.folder, [organize.Move("invoice.pdf", "Documents")])
            record.write_moves(self.folder, [organize.Move("holiday.jpg", "Images")])
        # Then: each was put in place by one rename onto .organize-last-run, from a hidden file
        # beside it, which the planner leaves in place, and from a different file each time, so
        # two runs at once never write the same new file
        self.assertEqual(len(renames), 2)
        for source, destination in renames:
            with self.subTest(source=source.name):
                self.assertEqual(destination, self.folder / RECORD_NAME)
                self.assertEqual(source.parent, self.folder)
                self.assertTrue(source.name.startswith("."))
        self.assertNotEqual(renames[0][0], renames[1][0])
