---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/16
stage: build
signoff: none
artifact-language: English
conversation-language: Japanese
---

# CLI tool to organize the Downloads folder

G1: A command-line tool, on Linux and macOS, that sorts the files directly in the user's ~/Downloads into folders by kind of file, such as Images, Documents, Videos, Music, Archives and Others, made inside Downloads, so that the user finds the file they want, where now too many files lie together to find it, and that can undo its last sort, moving each file it moved back to where it was, so that Downloads can be put back as it was. It only moves files, never deleting, renaming or overwriting one, the one thing it removes being a folder of a kind it made that undoing has left empty, and moves nothing unless told to, so that no file of the user's is lost or changed by it.

## Acceptance criteria

- AC1: Run on a folder without being told to move, the tool lists each file directly in that folder with the folder it would move to, and afterwards every file and folder in it is where it was, with the same name and content.
- AC2: Run told to move, the tool moves each file directly in the folder into the folder of its kind inside it, making that folder where it is not there, a file of no kind the README lists going to Others; each file inside a subfolder stays where it was; a hidden file, whose name starts with '.', and a download still running, whose name ends in .crdownload or .part, are not moved, stay where they were, and are named in the tool's output as left for that reason.
- AC3: A file whose name already exists in the folder it would move to is not moved, stays where it was, and is named in the tool's output as left for that reason; after any run, every file there was before is still there with the same name and content, no file overwritten.
- AC4: AC1 to AC3 and AC8 hold on a trial folder holding at least images, documents, a file of no listed kind, a name already taken in a target folder, a subfolder with files in it, a hidden file, a download still running, and, after a sort, a new file of the same name as one the sort moved, put where that one was; shown by automated tests and by real runs of the tool on Linux; run with no folder named, the tool works on ~/Downloads.
- AC5: The user installs the tool on their Mac as the README says and runs it once without being told to move, and it lists the files and the folders they would move to as AC1 says.
- AC6: The user runs the tool once without being told to move on their own ~/Downloads, and finds the folders it would sort the files into acceptable for finding a file.
- AC7: The README says how to install the tool and how to use it, undoing included, the kinds and which files belong to each included, and a reader following it from a fresh clone installs the tool and runs it to sort and to undo, each both without being told to move and told to move.
- AC8: Run to undo without being told to move, the tool lists each file the last sort moved, the sort being the last run told to move that was not to undo, with the place it would go back to, and afterwards every file and folder is where it was; run to undo and told to move, it moves each file the last sort moved back to where it was, one by one, and removes each folder that sort made that is then empty; a file whose old place now holds a file of the same name is not moved back, stays where it is, and is named in the tool's output as left for that reason; a folder that was there before that sort, or that still holds anything, is not removed.

## Tasks

- T5: `sort-downloads --undo`, which shows what undoing the last sort would move back and leave, and with `--move` moves each file back and removes each folder that sort made once empty. Serves AC3, AC4 and AC8.

  Completion criterion: unit tests show, on a folder made as AC4's trial folder, sorted and then given a new file where a moved one was, the undo listing and moves AC8 and the README's Example give, the file whose old place is taken left and named, only the empty folders the sort made removed, and nothing moved without `--move`; property tests show, over any file names, that a sort and its undo leave every file where it was with the same name and content and that no run writes over a file; mutation testing finds a test failing on each change it makes; and they pass, with the formatter, linter and type checker, on Python 3.9.

  Test: `uv run --directory sort-downloads --no-project --python 3.9 --with ruff --with mypy --with coverage --with hypothesis --with mutmut --with pytest sh -c 'ruff format --check . && ruff check . && mypy . && coverage run --branch -m unittest && coverage report && python -m unittest tests.properties && mutmut run'`

  - [x] 1. Make the unit tests of the undo from AC8 and the README's Example, seen failing on the tool of T4, `sort-downloads/tests/test_undo.py` as a code work. turn.
  - [ ] 2. Make the property tests the architecture names, seen failing on the tool of T4, `sort-downloads/tests/properties.py` as a code work. turn.
  - [ ] 3. Make the tool's Undo planner and the Mover's undo, `sort-downloads/sort_downloads.py` as a code work. turn.

- T6: The real runs of the installed `sort-downloads` on Linux. Serves AC4.

  Completion criterion: the record shows, each on a new copy of AC4's trial folder, the tool installed as the README says, then run with no `--move`, with `--move`, with `--undo` and with `--undo --move`, and with no folder named where `HOME` holds the trial folder as `Downloads`, each run's output as printed, and every file's name, place and checksum before and after each run meeting AC1 to AC3 and AC8.

  - [ ] 1. Run the installed tool on Linux as the architecture's Test says and record what was run and what came out, `.rn/20261027-organize-downloads-cli/trial-linux-runs.md` as a trial work. turn.

- T7: The README made again on the built tool, `sort-downloads/README.md`. Serves AC7.

  Completion criterion: a newcomer following it from a fresh clone of the branch installs the tool, runs it to sort and to undo, each with no `--move` and with `--move`, and gets what it shows, with the kinds and the files of each as the tool sorts them.

  - [ ] 1. Make the README again from the built tool, `sort-downloads/README.md` as a readme work. turn.

- T8: The architecture made again on the built tool, `sort-downloads/docs/architecture.md`. Serves AC1, AC2, AC3, AC4 and AC8.

  Completion criterion: each component, file and check it names is there in the built tool and its tests, as it says.

  - [ ] 1. Make the architecture again from the built tool, `sort-downloads/docs/architecture.md` as an architecture work. turn.

- T9: The user's own run on their Mac. Serves AC5 and AC6.

  Completion criterion: the user says that, installed on their Mac as the README says and run with no `--move` on their own `~/Downloads`, the tool listed the files and the folders they would move to as AC1 says, and that they find those folders acceptable for finding a file.

  - [ ] 1. Have the user install the tool on their Mac as the README says, run it once with no `--move` on their `~/Downloads`, and say what it listed and whether its folders suit finding a file. The orchestrator, with the user.

## Next

Step 4 of /rn:up on T5: action 2, the property tests

## Open

None.
