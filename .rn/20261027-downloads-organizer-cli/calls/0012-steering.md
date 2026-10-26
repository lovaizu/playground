# Command-line tool to organize the Downloads folder

G1: A command-line tool for macOS and Linux that moves the files directly in the user's Downloads
folder into folders by kind, and can move back what its last run moved, because today the user
cannot quickly find the file they are looking for there and wants to find it by what kind of file it
is; the tool itself, not a setting, makes sure no file is ever deleted, renamed or overwritten.

## Acceptance criteria

- AC1: Installed from this repository with `pipx install .`, the tool runs from any directory as a
  command of its own, such as `organize-downloads`, with Python 3 on macOS and Linux, and
  `pipx uninstall` removes it.
- AC2: By default the tool works on the `Downloads` folder under the user's home; given another
  folder, it works on that folder instead.
- AC3: Run without being told to move, the tool shows each file it would move with the kind folder it
  would go to, and changes nothing in the folder.
- AC4: Told to move, the tool moves each file directly in the folder whose extension is in its
  built-in table into the folder of that kind: images, documents, archives, audio, video or
  installers.
- AC5: In a run of AC3 or of AC4 these stay where they are and are shown as left in place: a file whose
  name is already taken in its kind folder; a file whose extension is not in the table, or that has
  none, such as a file still being downloaded (`.crdownload`, `.part`, `.download`) or a hidden file
  (`.DS_Store`); and each subfolder with what it holds.
- AC6: After any run of AC3, AC4, AC9 or AC10, every file that was in the folder, its subfolders
  included, is either where it was before the run or where the run moved it, under the same name and
  with the same content; none is deleted, renamed or overwritten.
- AC7: The repository holds automated tests that build a test folder with a file for each case of
  AC3 to AC6 and AC9 to AC11, check each of those criteria on it and pass, never touching the user's
  real Downloads folder or the user's own record of a last run.
- AC8: The README says how to install the tool, show the planned moves, make the moves, work on
  another folder, show and make the moves back of an undo, and remove the tool, so that following it
  alone the user can run the tool on a test Downloads folder of their own making.
- AC9: Asked to undo without being told to move, the tool shows each file the last run of AC4 on that
  folder moved, with where it would go back to, and each file it could not move back with the reason,
  and changes nothing in the folder.
- AC10: Asked to undo and told to move, the tool moves each file the last run of AC4 on that folder
  moved back to where it was, and then removes each kind folder that run newly made and that is now
  empty; a kind folder holding anything, or one that was there before that run, stays.
- AC11: In a run of AC9 or of AC10, a file stays where it is and is shown as not moved back, with the
  reason, when a file of the same name is now where it was or when it is no longer in its kind folder;
  the other files are moved back as AC10 says.
- AC12: The tool keeps what each run of AC4 moved, from where to where, in a place of its own under
  the user's home (`~/.local/state/organize-downloads` on Linux, `~/Library/Application
  Support/organize-downloads` on macOS), one record for each folder, so the organized folder gains no
  file of the tool's.

## Tasks

- T5: The tool showing the planned moves, the scene "Seeing the planned moves" of `docs/ux.md`, built as `docs/architecture.md` lays out. Serves AC2, AC3, AC5, AC7.

  Completion criterion: Run without `--move` on a test folder holding a file of each kind, a file
  whose name is taken in its kind folder, files of no kind, still being downloaded or hidden, and a
  subfolder, and on the default folder under a stand-in home, the tool prints each planned move and
  each file left in place with its reason as `docs/ux.md` shows them, and changes nothing; checked
  by the automated tests, which never touch the real Downloads folder or the user's record, passing
  on Linux here and on macOS and Linux on GitHub Actions.

  Test: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_preview.py'`

  - [ ] 1. The tests of showing the planned moves, from `docs/ux.md` and `docs/architecture.md`, seen failing on what is there, `tests/test_preview.py` as a code work. turn.
  - [ ] 2. The tool's package and its preview run, from `docs/ux.md`, `docs/architecture.md` and `tests/test_preview.py`, `src/organize_downloads/` as a code work. turn.

- T6: The tool moving the files, the scene "Organizing" of `docs/ux.md`, with the record of the run. Serves AC4, AC5, AC6, AC7, AC12.

  Completion criterion: Run with `--move` on the test folder of T5 under a stand-in home, the tool
  moves each file the preview showed into its kind folder by the one-step rename that refuses a
  taken name, leaves the rest with their reasons, keeps the run's moves in the record under the
  stand-in home and nothing in the folder, and after it every file is where it was or in its kind
  folder with the same name and content; checked by the automated tests, passing on Linux here and on
  macOS and Linux on GitHub Actions.

  Test: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_move.py'`

  - [ ] 1. The tests of moving the files and keeping the record, from `docs/ux.md` and `docs/architecture.md`, seen failing on what is there, `tests/test_move.py` as a code work. turn.
  - [ ] 2. The move run, the Mover and the Record store, from `docs/ux.md`, `docs/architecture.md`, `.rn/20261027-downloads-organizer-cli/trial-rename.md` and `tests/test_move.py`, `src/organize_downloads/` as a code work. turn.

- T7: The tool undoing the last move run, the scenes "Seeing the planned moves back" and "Undoing" of `docs/ux.md`. Serves AC6, AC7, AC9, AC10, AC11.

  Completion criterion: After a move run of T6 on a test folder under a stand-in home, with one file
  whose old place is now taken and one no longer in its kind folder, `--undo` shows each move back,
  each file not moved back with its reason and each kind folder to remove, and changes nothing;
  `--undo --move` makes those moves back, removes only the kind folders that run made and that are
  now empty, keeps in the record the moves not made, and leaves every file where it was or where it
  was moved back, with the same name and content; checked by the automated tests, passing on Linux
  here and on macOS and Linux on GitHub Actions.

  Test: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_undo.py'`

  - [ ] 1. The tests of undoing, from `docs/ux.md` and `docs/architecture.md`, seen failing on what is there, `tests/test_undo.py` as a code work. turn.
  - [ ] 2. The undo runs and the Undo planner, from `docs/ux.md`, `docs/architecture.md` and `tests/test_undo.py`, `src/organize_downloads/` as a code work. turn.

- T8: The README made again on the built tool, with the LICENSE file it names. Serves AC1, AC8.

  Completion criterion: Following `README.md` alone on the built tool, a newcomer installs it with
  `pipx install .`, runs `organize-downloads` from another directory, shows and makes the moves and
  the moves back on a test folder of their own making, sees each output as the README shows it, and
  removes it with `pipx uninstall`; the README also says what happens on a file system that refuses
  the one-step rename, and the repository holds the MIT `LICENSE`. Checked by an AI that did not make
  it, doing so in a newcomer's place.

  - [ ] 1. The README made again from the built tool and `docs/ux.md`, with the LICENSE file, `README.md` as a readme work. turn.

- T9: The architecture made again on the built tool. Serves AC7.

  Completion criterion: Whoever changes the tool can tell from `docs/architecture.md`, held against
  the built code and tests, each part where it is placed, how it acts on the others and how each is
  checked, with no line the built tool does not hold. Checked by an AI that did not make it, reading
  it with the built tool in a maintainer's place.

  - [ ] 1. The architecture made again from the built tool, `docs/architecture.md` as an architecture work. turn.
