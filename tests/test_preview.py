"""Tests of the preview run: `organize-downloads` without `--move`.

They hold what docs/ux.md asks of it, under "The whole way" and "Seeing the planned moves": which
folder a run is about, the planned move it shows for each file whose kind is known and whose name
is free in its kind folder, the reason it shows for each file and subfolder left in place, and that
it changes nothing.  Every expected line is written here from docs/ux.md, never taken from the tool.

Each test builds its own stand-in home in a new temporary folder and sets `HOME` to it, so no test
touches the real Downloads folder or the user's own record of a last run, and two runs of the tests
at the same time never share a folder.  The Command is called in this process, as
`organize_downloads.cli.main(<the words after the command>)`, with what it prints caught.

The tests run on Python 3.9 and every later Python 3, the oldest the user decided the tool and its
tests run on, so a Mac user can run them with the python3 of Apple's command line tools; they use
nothing newer than 3.9 offers.

Coverage measurement and mutation testing are left out of these tests: the user decided so, as the
tool and its tests use Python's standard library alone and neither check is in it.  In their place
the tests take a case from each case and reason of docs/ux.md, and the property tests make many
folders with Python's own `random` module on each run.
"""

import contextlib
import io
import os
import random
import shutil
import tempfile
import unittest
from typing import Dict, List, Optional
from unittest import mock

from organize_downloads import cli

# The kind table of docs/ux.md, "Seeing the planned moves": each kind folder with its extensions.
KIND_TABLE: Dict[str, List[str]] = {
    "images": ["jpg", "jpeg", "png", "gif", "webp", "heic", "heif", "bmp", "tif", "tiff", "svg"],
    "documents": ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "rtf",
                  "txt", "md", "csv", "epub", "pages", "numbers", "key"],
    "archives": ["zip", "tar", "gz", "tgz", "bz2", "xz", "7z", "rar"],
    "audio": ["mp3", "wav", "flac", "aac", "m4a", "ogg", "opus"],
    "video": ["mp4", "mov", "mkv", "avi", "webm", "m4v"],
    "installers": ["dmg", "pkg", "deb", "rpm", "appimage", "exe", "msi"],
}
KIND_OF_EXTENSION: Dict[str, str] = {
    extension: kind for kind, extensions in KIND_TABLE.items() for extension in extensions
}

# The last line of a preview run in docs/ux.md.
LAST_LINE = "Nothing changed. Run with --move to make these moves."

# How each line about one file or subfolder begins in docs/ux.md: a planned move, or left in place.
WOULD_MOVE = "would move  "
LEFT = "left  "

# A tree of files and folders: each path, relative to the tree's top and with "/" between its
# parts, mapped to the file's bytes, or to None for a folder.
Tree = Dict[str, Optional[bytes]]


def would_move(name: str, kind: str) -> str:
    """Give the line docs/ux.md shows for a file `name` a move run would put in `kind`."""
    return f"{WOULD_MOVE}{name}  ->  {kind}/{name}"


def left(name: str, reason: str) -> str:
    """Give the line docs/ux.md shows for `name` left in place with `reason`.

    For a subfolder, `name` is given with its trailing "/", as docs/ux.md prints it.
    """
    return f"{LEFT}{name}  {reason}"


def entry_lines(lines: List[str]) -> List[str]:
    """Give, sorted, the lines of `lines` about one file or subfolder each.

    docs/ux.md sets no order for them, and taking them out by how they begin lets a test of
    them pass or fail on them alone, whatever the first and last lines are.
    """
    return sorted(line for line in lines if line.startswith((WOULD_MOVE, LEFT)))


def kind_of(name: str) -> Optional[str]:
    """Give the kind folder docs/ux.md puts a file called `name` in, or None for no known kind.

    The extension is only the part after the last dot, read without regard to case, so `.png`
    has the extension png; a name with no dot has none.  Used only to build the expected lines of
    the property tests.
    """
    if "." not in name:
        return None
    return KIND_OF_EXTENSION.get(name.rsplit(".", 1)[1].lower())


def build(top: str, tree: Tree) -> None:
    """Make every file and folder of `tree` under the folder `top`, which must already exist."""
    for path, content in sorted(tree.items()):
        full = os.path.join(top, *path.split("/"))
        if content is None:
            os.makedirs(full, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(content)


def read_tree(top: str) -> Tree:
    """Give every file and folder under the folder `top`, as a `Tree`, symbolic links as files.

    A symbolic link is read as its target's path, so a link changed or followed shows as changed.
    """
    found: Tree = {}
    for root, folders, files in os.walk(top):
        for name in folders + files:
            full = os.path.join(root, name)
            path = os.path.relpath(full, top).replace(os.sep, "/")
            if os.path.islink(full):
                found[path] = ("link to " + os.readlink(full)).encode()
            elif os.path.isdir(full):
                found[path] = None
            else:
                with open(full, "rb") as f:
                    found[path] = f.read()
    return found


class PreviewTestCase(unittest.TestCase):
    """A stand-in home for each test, and the running of a preview run in it."""

    def setUp(self) -> None:
        # The home is given by its full path with symbolic links resolved, as the Command names
        # folders that way, such as /private/var/... for /var/... on macOS.
        self.home = os.path.realpath(tempfile.mkdtemp(prefix="organize-downloads-test-"))
        self.addCleanup(shutil.rmtree, self.home)
        self.downloads = os.path.join(self.home, "Downloads")

    def make_folder(self, tree: Tree, name: str = "Downloads") -> str:
        """Make the folder `name` under the stand-in home holding `tree`, and give its full path."""
        folder = os.path.join(self.home, name)
        os.makedirs(folder)
        build(folder, tree)
        return folder

    def preview(self, *words: str) -> List[str]:
        """Run `organize-downloads <words>` with `HOME` set to the stand-in home.

        Gives each line it prints, on standard output or standard error, in the order printed.
        A stop by `SystemExit` is taken as the end of the run, as docs/ux.md sets no exit status.
        """
        printed = io.StringIO()
        with mock.patch.dict(os.environ, {"HOME": self.home}), \
                contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            try:
                cli.main(list(words))
            except SystemExit:
                pass
        return printed.getvalue().splitlines()

    def assert_entries(self, lines: List[str], expected: List[str], msg: str = "") -> None:
        """Check that the lines about files and subfolders in `lines` are `expected`, each once."""
        self.assertEqual(entry_lines(lines), sorted(expected), f"{msg}\nprinted: {lines}")


class WhichFolderTest(PreviewTestCase):
    """"The whole way": the `Downloads` folder under the home, or the folder given as last word.

    The first line a run prints names the folder; these tests check that line, or the line said
    when there is no folder.
    """

    def test_without_a_folder_given_it_names_downloads_under_the_home(self) -> None:
        # Given: a home whose Downloads folder holds report.pdf.
        self.make_folder({"report.pdf": b"report"})
        # When: the user runs organize-downloads with no folder.
        lines = self.preview()
        # Then: its first line names the Downloads folder by its full path.
        self.assertEqual(lines[:1], [f"Folder: {self.downloads}"])

    def test_a_folder_given_is_named_in_place_of_downloads(self) -> None:
        # Given: a home with a Downloads folder and a Desktop folder.
        self.make_folder({"report.pdf": b"report"})
        desktop = self.make_folder({"photo.png": b"photo"}, "Desktop")
        # When: the user runs organize-downloads with the Desktop folder as last word.
        lines = self.preview(desktop)
        # Then: its first line names the Desktop folder.
        self.assertEqual(lines[:1], [f"Folder: {desktop}"])

    def test_a_folder_given_has_its_own_files_shown_and_not_those_of_downloads(self) -> None:
        # Given: a home with a Downloads folder holding report.pdf and a Desktop folder holding
        # photo.png.
        self.make_folder({"report.pdf": b"report"})
        desktop = self.make_folder({"photo.png": b"photo"}, "Desktop")
        # When: the user runs organize-downloads with the Desktop folder as last word.
        lines = self.preview(desktop)
        # Then: photo.png is shown in some line and report.pdf in none.
        self.assertTrue(any("photo.png" in line for line in lines), lines)
        self.assertFalse(any("report.pdf" in line for line in lines), lines)

    def test_a_folder_given_by_a_relative_path_is_named_by_its_full_path(self) -> None:
        # Given: a Desktop folder, and the home as the working folder.
        desktop = self.make_folder({"photo.png": b"photo"}, "Desktop")
        old_working_folder = os.getcwd()
        os.chdir(self.home)
        self.addCleanup(os.chdir, old_working_folder)
        # When: the user runs organize-downloads Desktop.
        lines = self.preview("Desktop")
        # Then: its first line names the folder by its full path.
        self.assertEqual(lines[:1], [f"Folder: {desktop}"])

    def test_a_folder_given_by_a_symbolic_link_is_named_by_the_folder_it_leads_to(self) -> None:
        # Given: a Desktop folder, and a symbolic link to it called Shortcut.
        desktop = self.make_folder({"photo.png": b"photo"}, "Desktop")
        os.symlink(desktop, os.path.join(self.home, "Shortcut"))
        # When: the user runs organize-downloads with the link as last word.
        lines = self.preview(os.path.join(self.home, "Shortcut"))
        # Then: its first line names the Desktop folder, as docs/architecture.md resolves
        # symbolic links.
        self.assertEqual(lines[:1], [f"Folder: {desktop}"])

    def test_a_folder_given_that_does_not_exist_is_said_and_nothing_changes(self) -> None:
        # Given: a home holding a Downloads folder with report.pdf and no Desktop folder.
        self.make_folder({"report.pdf": b"report"})
        before = read_tree(self.home)
        missing = os.path.join(self.home, "Desktop")
        # When: the user runs organize-downloads with the missing Desktop folder.
        lines = self.preview(missing)
        # Then: it prints only that there is no folder there, and the home is as it was.
        self.assertEqual(lines, [f"No folder at {missing}."])
        self.assertEqual(read_tree(self.home), before)

    def test_a_path_given_that_is_a_file_is_said_to_be_no_folder(self) -> None:
        # Given: a home holding a file called notes.txt.
        build(self.home, {"notes.txt": b"notes"})
        before = read_tree(self.home)
        path = os.path.join(self.home, "notes.txt")
        # When: the user runs organize-downloads with notes.txt as last word.
        lines = self.preview(path)
        # Then: it prints that there is no folder there, and the home is as it was.
        self.assertEqual(lines, [f"No folder at {path}."])
        self.assertEqual(read_tree(self.home), before)

    def test_without_a_folder_given_and_no_downloads_it_says_there_is_no_folder(self) -> None:
        # Given: a home with no Downloads folder.
        # When: the user runs organize-downloads with no folder.
        lines = self.preview()
        # Then: it prints that there is no folder at Downloads under the home, and makes none.
        self.assertEqual(lines, [f"No folder at {self.downloads}."])
        self.assertEqual(read_tree(self.home), {})


class PrintoutTest(PreviewTestCase):
    """"Seeing the planned moves": the shape of what a preview prints, around the lines of files."""

    def test_the_last_line_says_nothing_changed_and_how_to_make_the_moves(self) -> None:
        # Given: a folder holding report.pdf.
        self.make_folder({"report.pdf": b"report"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: its last line says nothing changed and how to make these moves.
        self.assertEqual(lines[-1:], [LAST_LINE])

    def test_an_empty_folder_also_ends_with_the_last_line(self) -> None:
        # Given: an empty Downloads folder.
        self.make_folder({})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: its last line says nothing changed and how to make these moves.
        self.assertEqual(lines[-1:], [LAST_LINE])

    def test_between_the_first_and_last_lines_there_is_one_line_for_each_entry(self) -> None:
        # Given: a folder holding a file that would move, one left in place and a subfolder.
        self.make_folder({"report.pdf": b"1", "film.part": b"2", "projects/plan.txt": b"3"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: the lines between the first and the last are three, each about one entry.
        self.assertEqual(len(lines[1:-1]), 3, lines)
        self.assertEqual(sorted(lines[1:-1]), entry_lines(lines), lines)


class PlannedMoveTest(PreviewTestCase):
    """"Seeing the planned moves": each file of a known kind whose name is free, with its kind."""

    def test_every_extension_of_the_kind_table_would_go_to_its_kind_folder(self) -> None:
        # Given: a folder holding one file for each extension of the kind table.
        names = {f"file-{extension}.{extension}": kind
                 for extension, kind in KIND_OF_EXTENSION.items()}
        self.make_folder({name: name.encode() for name in names})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: each file would move to the kind folder the table gives its extension.
        self.assert_entries(lines, [would_move(name, kind) for name, kind in names.items()])

    def test_an_extension_in_upper_or_mixed_case_goes_where_its_lower_case_goes(self) -> None:
        # Given: a folder holding photo.JPG, report.Pdf and song.MP3.
        self.make_folder({"photo.JPG": b"1", "report.Pdf": b"2", "song.MP3": b"3"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: each would move to the kind folder of its extension in lower case.
        self.assert_entries(lines, [
            would_move("photo.JPG", "images"),
            would_move("report.Pdf", "documents"),
            would_move("song.MP3", "audio"),
        ])

    def test_only_the_part_after_the_last_dot_is_the_extension(self) -> None:
        # Given: a folder holding backup.tar.gz and scan.pdf.png.
        self.make_folder({"backup.tar.gz": b"1", "scan.pdf.png": b"2"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: backup.tar.gz would go to archives and scan.pdf.png to images.
        self.assert_entries(lines, [
            would_move("backup.tar.gz", "archives"),
            would_move("scan.pdf.png", "images"),
        ])

    def test_a_name_starting_with_a_dot_has_the_part_after_its_last_dot_as_extension(self) -> None:
        # Given: a folder holding .png, whose only dot is its first character, and .notes.pdf.
        self.make_folder({".png": b"1", ".notes.pdf": b"2"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: .png would go to images and .notes.pdf to documents.
        self.assert_entries(lines, [
            would_move(".png", "images"),
            would_move(".notes.pdf", "documents"),
        ])

    def test_a_name_with_spaces_or_letters_beyond_ascii_is_shown_as_it_is(self) -> None:
        # Given: a folder holding "my report.pdf" and "写真.png".
        self.make_folder({"my report.pdf": b"1", "写真.png": b"2"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: each is shown with its name unchanged.
        self.assert_entries(lines, [
            would_move("my report.pdf", "documents"),
            would_move("写真.png", "images"),
        ])

    def test_a_free_name_in_a_kind_folder_already_there_would_move(self) -> None:
        # Given: a folder holding report.pdf and a documents folder holding another file.
        self.make_folder({"report.pdf": b"1", "documents/old.pdf": b"2"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: report.pdf would move into documents, which is left as a subfolder.
        self.assert_entries(lines, [
            would_move("report.pdf", "documents"),
            left("documents/", "subfolder"),
        ])

    def test_an_empty_folder_shows_no_file(self) -> None:
        # Given: an empty Downloads folder.
        self.make_folder({})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: no line is about a file or subfolder.
        self.assert_entries(lines, [])

    def test_the_files_of_the_example_of_docs_ux_are_shown_as_there(self) -> None:
        # Given: the folder of the example under "Seeing the planned moves" in docs/ux.md.
        self.make_folder({
            "report.pdf": b"1", "photo.JPG": b"2", "song.mp3": b"3", "audio/song.mp3": b"4",
            "setup.crdownload": b"5", ".DS_Store": b"6", "projects/plan.txt": b"7",
        })
        # When: the user runs a preview.
        lines = self.preview()
        # Then: the lines about its files and subfolders are those of that example.
        self.assert_entries(lines, [
            would_move("report.pdf", "documents"),
            would_move("photo.JPG", "images"),
            left("song.mp3", "name taken in audio/"),
            left("setup.crdownload", "kind not known"),
            left(".DS_Store", "kind not known"),
            left("audio/", "subfolder"),
            left("projects/", "subfolder"),
        ])


class LeftInPlaceTest(PreviewTestCase):
    """"Seeing the planned moves": each file and subfolder that stays, with its reason."""

    def test_a_file_whose_name_is_taken_in_its_kind_folder_is_left(self) -> None:
        # Given: a folder holding song.mp3 and an audio folder already holding a song.mp3.
        self.make_folder({"song.mp3": b"new", "audio/song.mp3": b"old"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: song.mp3 is left as its name is taken in audio/.
        self.assert_entries(lines, [
            left("song.mp3", "name taken in audio/"),
            left("audio/", "subfolder"),
        ])

    def test_a_file_of_unknown_or_no_extension_is_left_as_kind_not_known(self) -> None:
        # Given: a folder holding files still being downloaded, a hidden file, a file with no
        # extension, one ending in a dot and one whose extension is not in the kind table.
        names = ["setup.crdownload", "film.part", "app.download", ".DS_Store", "README",
                 "notes.", "data.xyz"]
        self.make_folder({name: b"x" for name in names})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: each is left as its kind is not known.
        self.assert_entries(lines, [left(name, "kind not known") for name in names])

    def test_a_subfolder_is_left_with_all_it_holds(self) -> None:
        # Given: a folder holding a projects folder with files and a folder of its own inside.
        self.make_folder({"projects/plan.pdf": b"1", "projects/old/photo.png": b"2"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: projects/ is left as a subfolder, and nothing inside it is shown.
        self.assert_entries(lines, [left("projects/", "subfolder")])

    def test_a_subfolder_named_like_a_file_of_a_known_kind_is_left_as_a_subfolder(self) -> None:
        # Given: a folder holding a folder called photos.jpg.
        self.make_folder({"photos.jpg/a.png": b"1"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: photos.jpg/ is left as a subfolder.
        self.assert_entries(lines, [left("photos.jpg/", "subfolder")])

    def test_each_kind_folder_already_there_is_left_as_a_subfolder(self) -> None:
        # Given: a folder holding every kind folder, each empty.
        self.make_folder({kind: None for kind in KIND_TABLE})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: each kind folder is left as a subfolder.
        self.assert_entries(lines, [left(f"{kind}/", "subfolder") for kind in KIND_TABLE])

    def test_a_file_whose_kind_folder_name_is_taken_by_a_file_is_left(self) -> None:
        # Given: a folder holding photo.png and a file called images.
        self.make_folder({"photo.png": b"1", "images": b"2"})
        # When: the user runs a preview.
        lines = self.preview()
        # Then: photo.png is left as images is not a folder, and the file images is left as its
        # kind is not known.
        self.assert_entries(lines, [
            left("photo.png", "images is not a folder"),
            left("images", "kind not known"),
        ])


class NothingChangedTest(PreviewTestCase):
    """"Seeing the planned moves": a preview changes nothing, in the folder or under the home."""

    def test_a_preview_changes_nothing_under_the_home(self) -> None:
        # Given: a folder holding a file of each case of docs/ux.md: one that would move, one
        # whose name is taken, one of no known kind, one whose kind folder is not a folder, and
        # a subfolder.
        self.make_folder({
            "report.pdf": b"1", "song.mp3": b"2", "audio/song.mp3": b"3", "film.part": b"4",
            "photo.png": b"5", "images": b"6", "projects/plan.txt": b"7",
        })
        before = read_tree(self.home)
        # When: the user runs a preview.
        self.preview()
        # Then: every file and folder under the home is as it was, and nothing is added, such as
        # a kind folder or a record.
        self.assertEqual(read_tree(self.home), before)


class RandomFolderTest(PreviewTestCase):
    """Property tests: many folders made at random on each run, each previewed once.

    The seed of each run is in the message of a failure; to run that case again, give it to
    `random.Random` in place of the random seed, and keep the folder it makes as a test above.
    """

    RUNS = 40

    def random_folder(self, rng: random.Random) -> Tree:
        """Make a folder of up to 12 entries mixing every case of docs/ux.md, picked by `rng`.

        Names may begin with a dot, as hidden files do.  Names differ in more than case, so the
        folder can be made on a file system that does not tell case apart, as macOS's usually
        does.
        """
        tree: Tree = {}
        used = set()

        def fresh(name: str) -> bool:
            if name.lower() in used:
                return False
            used.add(name.lower())
            return True

        for _ in range(rng.randint(0, 12)):
            stem = "".join(rng.choice("abcdefgXYZ019 -_.") for _ in range(rng.randint(0, 8)))
            case = rng.choice(["known", "known", "unknown", "none", "subfolder"])
            if case == "known":
                extension = rng.choice(list(KIND_OF_EXTENSION))
                extension = "".join(rng.choice([c.lower(), c.upper()]) for c in extension)
                name = f"{stem}.{extension}"
            elif case == "unknown":
                name = stem + rng.choice([".crdownload", ".part", ".download", ".xyz", "."])
            elif case == "none":
                name = stem.replace(".", "") or "f"
            else:
                name = stem
            # "." and ".." name no entry of their own, and "" names none at all.
            if name in ("", ".", "..") or name.lower() in KIND_TABLE or not fresh(name):
                continue
            if case == "subfolder":
                tree[name] = None
                tree[f"{name}/inner.png"] = b"inner"
            else:
                tree[name] = name.encode()

        # Some kind folders: absent, a folder holding some of the names, or a file.
        for kind in KIND_TABLE:
            state = rng.choice(["absent", "absent", "folder", "file"])
            if state == "folder":
                tree[kind] = None
                for name, content in list(tree.items()):
                    if content is not None and "/" not in name and kind_of(name) == kind \
                            and rng.random() < 0.5:
                        tree[f"{kind}/{name}"] = b"already there"
            elif state == "file":
                tree[kind] = b"not a folder"
        return tree

    def expected_lines(self, tree: Tree) -> List[str]:
        """Give the line docs/ux.md asks for each entry directly in a folder holding `tree`."""
        lines = []
        for name, content in tree.items():
            if "/" in name:
                continue
            if content is None:
                lines.append(left(f"{name}/", "subfolder"))
                continue
            kind = kind_of(name)
            if kind is None:
                lines.append(left(name, "kind not known"))
            elif tree.get(kind, None) is not None:
                lines.append(left(name, f"{kind} is not a folder"))
            elif f"{kind}/{name}" in tree:
                lines.append(left(name, f"name taken in {kind}/"))
            else:
                lines.append(would_move(name, kind))
        return lines

    def test_every_entry_of_a_random_folder_is_shown_once_as_docs_ux_says(self) -> None:
        seed = random.randrange(2 ** 32)
        rng = random.Random(seed)
        for run in range(self.RUNS):
            # Given: a folder made at random.
            tree = self.random_folder(rng)
            folder = self.make_folder(tree, f"folder-{run}")
            # When: the user runs a preview of it.
            lines = self.preview(folder)
            # Then: each entry directly in it is shown once, with the line docs/ux.md asks.
            self.assert_entries(lines, self.expected_lines(tree),
                                f"seed {seed}, run {run}, folder {sorted(tree)}")

    def test_a_preview_of_a_random_folder_changes_nothing_under_the_home(self) -> None:
        seed = random.randrange(2 ** 32)
        rng = random.Random(seed)
        for run in range(self.RUNS):
            # Given: a folder made at random.
            folder = self.make_folder(self.random_folder(rng), f"folder-{run}")
            before = read_tree(self.home)
            # When: the user runs a preview of it.
            self.preview(folder)
            # Then: every file and folder under the home is as it was.
            self.assertEqual(read_tree(self.home), before, f"seed {seed}, run {run}")
