---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/14
stage: plan
signoff: none
artifact-language: English
conversation-language: Japanese
---

# Command-line tool to organize the Downloads folder

G1: A command-line tool for macOS and Linux that moves the files directly in the user's Downloads
folder into folders by kind, because today the user cannot quickly find the file they are looking
for there and wants to find it by what kind of file it is; the tool itself, not a setting, makes sure
no file is ever deleted, renamed or overwritten.

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
- AC6: After any run, every file that was in the folder, its subfolders included, is either where it
  was or in its kind folder, under the same name and with the same content; none is deleted, renamed
  or overwritten.
- AC7: The repository holds automated tests that build a test folder with a file for each case of
  AC3 to AC6, check each of those criteria on it and pass, never touching the user's real Downloads
  folder.
- AC8: The README says how to install the tool, show the planned moves, make the moves, work on
  another folder and remove the tool, so that following it alone the user can run the tool on a test
  Downloads folder of their own making.

## Next

Step 8 of /rn:up on plan: stop at the plan sign-off

## Open

None.
