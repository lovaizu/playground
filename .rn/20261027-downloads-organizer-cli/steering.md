---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/14
stage: design
signoff: none
artifact-language: English
conversation-language: Japanese
---

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

- T3: The architecture of the tool. Serves AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC8, AC9, AC10, AC11, AC12.

  Completion criterion: Whoever builds the tool can tell from the architecture, with the UX `docs/ux.md`
  and the README `README.md`, each part of the tool, how the parts keep any file from being deleted,
  renamed or overwritten, in organizing and in undoing, what the record of a run holds and where, and
  how each part and each criterion is checked by the automated tests of AC7. Checked by an AI that
  did not make it, reading it in the builder's place.

  - [ ] 1. The architecture made from the UX `docs/ux.md` and the README `README.md`, `docs/architecture.md` as an
    architecture work. turn.

## Next

Step 4 of /rn:up on T3: action 1

## Open

None.
