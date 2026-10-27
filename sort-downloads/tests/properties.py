"""Property tests of the sort and its undo: sort-downloads run on folders of any names.

Over folders Hypothesis makes, holding files and folders of any names, they check two
things the plan (.rn/20261027-organize-downloads-cli/steering.md) asks after any run:
by AC8, a sort followed by its undo leaves every file and folder where it was, with the
same name and content; by AC3, no run writes over a file, so after each run, in any
order, every file there was before it is still there with the same name and content.

They are run on their own, by `python3 -m unittest tests.properties` with Hypothesis
installed, as docs/architecture.md's Test says, so the unit test run never meets
Hypothesis. Each input runs the tool's main() with the unit tests' helpers and set-up:
on a folder made for it in a temporary folder, with HOME and XDG_STATE_HOME pointed
into that folder, so no input reads or changes the files of the machine it runs on, or
another input's record.
"""

from __future__ import annotations

import contextlib
import os
import unicodedata
import unittest
from collections.abc import Iterator
from pathlib import Path

from hypothesis import example, given, settings
from hypothesis import strategies as st

import tests.test_preview
from tests.test_preview import (
    EXAMPLE_FILES,
    make_files,
    readme_kinds,
    run_tool,
    snapshot,
)
from tests.test_sort import files_by_name
from tests.test_undo import snapshot_of

# The kind folders of the README's table, and Others, the folder its last row names.
KIND_FOLDERS = [*readme_kinds(), "Others"]

# The endings a name may be given: each the README's table lists, and each in
# capitals, as the README counts capitals the same; those it names for a download
# still running; and "" for none, which the table's Others row takes.
ENDINGS = [
    "",
    ".crdownload",
    ".part",
    *sorted(
        variant
        for endings in readme_kinds().values()
        for ending in endings
        for variant in (ending, ending.upper())
    ),
]

# Any text a name holds on Linux and macOS: every character UTF-8 can write, which
# leaves out the lone surrogates Python cannot turn into a file name, but "/", which
# parts a path, and NUL, which ends one. Ten at most keeps a name, in UTF-8's four
# bytes a character at most, inside the 255 bytes a file system allows.
STEMS = st.text(st.characters(codec="utf-8", exclude_characters="/\x00"), max_size=10)

# A file or folder name: a kind folder's own name, which takes the place its kind's
# files need; or any text, hidden or not, ending in one of ENDINGS or in none. "." and
# "..", which name the folder and the one above it, and "", are no file's name.
NAMES = st.one_of(
    st.sampled_from(KIND_FOLDERS),
    st.builds(
        lambda dot, stem, ending: dot + stem + ending,
        st.sampled_from(["", "."]),
        STEMS,
        st.sampled_from(ENDINGS),
    ),
).filter(lambda name: name not in ("", ".", ".."))

# A step of a sequence of runs where SAVE stands, the user saving a new file in the
# folder; each other step is the arguments of a run of the tool.
SAVE = None

# Each run of the tool there is: the preview and the sort, to which the folder is
# given after the arguments, and the undo, without and with --move, given no folder.
RUNS: tuple[list[str], ...] = ([], ["--move"], ["--undo"], ["--undo", "--move"])


def place_key(name: str) -> str:
    """Give the key two names share where a file system may take them for one name.

    macOS's file systems count capitals as small letters and the two ways Unicode
    writes an accented letter as one, so names of one key are not made together; what
    each property compares is read back from the folder, not taken from the names.

    Args:
        name: A file or folder name.

    Returns:
        The name decomposed, as Unicode's NFD form writes it, and casefolded.
    """
    return unicodedata.normalize("NFD", name).casefold()


@st.composite
def layouts(draw: st.DrawFn) -> dict[str, bytes | None]:
    """Make the files and folders of a folder to sort.

    Directly in it are files, and folders each holding files or nothing: a kind
    folder there before the sort, or one of the user's own. Each file's content is its
    path, so a file swapped for another is seen.

    Args:
        draw: Hypothesis's draw, which takes a value from a strategy.

    Returns:
        Each path inside the folder, with "/" between parts, with a file's content or
        None for a folder, as snapshot() gives them.
    """
    entries = draw(
        st.lists(
            st.tuples(
                NAMES, st.none() | st.lists(NAMES, unique_by=place_key, max_size=3)
            ),
            unique_by=lambda entry: place_key(entry[0]),
            max_size=8,
        )
    )
    layout: dict[str, bytes | None] = {}
    for name, inside in entries:
        if inside is None:
            layout[name] = name.encode()
            continue
        layout[name] = None
        for inner in inside:
            path = f"{name}/{inner}"
            layout[path] = path.encode()
    return layout


def make_layout(folder: Path, layout: dict[str, bytes | None]) -> None:
    """Make each file and folder of a layout inside the folder.

    Args:
        folder: The folder to make them in.
        layout: The files and folders, as layouts() gives them.
    """
    for path, content in layout.items():
        if content is None:
            (folder / path).mkdir(exist_ok=True)
    files = {path: content for path, content in layout.items() if content is not None}
    make_files(folder, files)


def save_new_files(folder: Path, layout: dict[str, bytes | None]) -> None:
    """Save a new file where each file the layout puts directly in the folder is not.

    This is AC4's new file of the same name as one the sort moved, put where that one
    was, for every such file at once.

    Args:
        folder: The folder.
        layout: Its files and folders before the first run, as layouts() gives them.
    """
    for path, content in layout.items():
        if content is not None and "/" not in path:
            place = folder / path
            # lexists: a file there, or a link even to nothing, keeps its place.
            if not os.path.lexists(place):
                place.write_bytes(b"saved since: " + content)


@contextlib.contextmanager
def trial() -> Iterator[tests.test_preview.TestPreview]:
    """Set up the unit tests' place for one input, and clear it after.

    Hypothesis runs a test's body once for each input, where unittest runs setUp once
    for the test, so the preview's tests' set-up, kept in one place, is run here for
    each input.

    Yields:
        A test of the preview set up, whose folder is an empty folder to sort, with
        HOME and XDG_STATE_HOME inside its root.
    """
    place = tests.test_preview.TestPreview()
    place.setUp()
    try:
        yield place
    finally:
        place.doCleanups()


# The settings of each property. deadline=None: an input's runs read and write files,
# whose time the machine sets, so no time limit fails a run that is only slow.
# database=None: Hypothesis keeps no failing input to try first on the next run, so no
# run's result hangs on an earlier one; an input that once failed is kept as an
# @example instead, beside the README's Example, AC4's trial folder, tried on each run.
TRIAL = settings(deadline=None, database=None)


class TestProperties(unittest.TestCase):
    @TRIAL
    @given(layouts())
    @example(snapshot_of(EXAMPLE_FILES))
    def test_a_sort_then_its_undo_leaves_every_file_and_folder_where_it_was(
        self, layout: dict[str, bytes | None]
    ) -> None:
        with trial() as place:
            # Given: a folder holding files and folders of any names.
            make_layout(place.folder, layout)
            before = snapshot(place.folder)
            # When: the tool is run on it with --move, then with --undo --move.
            sorted_run = run_tool(["--move", str(place.folder)])
            undone_run = run_tool(["--undo", "--move"])
            # Then: both runs end with no error, and every file and folder in it is
            # where it was with the same name and content, and nothing else is there.
            self.assertEqual((sorted_run[0], sorted_run[2]), (0, ""))
            self.assertEqual((undone_run[0], undone_run[2]), (0, ""))
            self.assertEqual(snapshot(place.folder), before)

    @TRIAL
    @given(layouts(), st.lists(st.sampled_from([*RUNS, SAVE]), max_size=6))
    @example(snapshot_of(EXAMPLE_FILES), [[], SAVE, ["--undo"], ["--undo", "--move"]])
    def test_no_run_writes_over_a_file(
        self, layout: dict[str, bytes | None], steps: list[list[str] | None]
    ) -> None:
        with trial() as place:
            # Given: a folder holding files and folders of any names, sorted first so
            # that each undo has a sort to undo.
            make_layout(place.folder, layout)
            for step in [["--move"], *steps]:
                # When: each run of the steps is made in their order, the user saving
                # a new file where each file first directly in it no longer is at
                # each SAVE.
                if step is SAVE:
                    save_new_files(place.folder, layout)
                    continue
                before = files_by_name(snapshot(place.folder))
                undo = "--undo" in step
                status, _, err = run_tool(step if undo else [*step, str(place.folder)])
                # Then: each run ends with no error, so it was made, and the folder
                # holds the same files by name and content, as many of each, as before
                # it, wherever each now is: none written over, renamed or lost.
                self.assertEqual((status, err), (0, ""), step)
                self.assertEqual(files_by_name(snapshot(place.folder)), before, step)
