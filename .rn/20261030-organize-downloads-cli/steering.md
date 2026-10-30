---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/20
stage: ux
signoff: none
artifact-language: English
conversation-language: Japanese
---

# Downloads folder organizer CLI

G1: Files pile up in the user's Downloads folder and they cannot find the one they want. A
command-line tool for macOS and Linux sorts the files there by type into one folder per type inside
Downloads itself, so a file is found by opening the folder of its type, while no file is ever
deleted, renamed or overwritten. The README tells how to install and use it, and tests check what
it does.

## Acceptance criteria

- AC1: Run plainly, with no instruction to move, on the trial folder, the tool prints a list giving
  each file of the six types (Images, Documents, Archives, Audio, Video, Installers, told apart by
  extension) with the type folder it would move to, each file of no type as not moved, and the
  same-name file as not moved because of the same name; afterwards every file and folder is where it
  was. The trial folder is a folder holding files of all six types, a file with no extension, a file
  with an extension of none of the six types, a folder, a hidden file such as `.DS_Store`, and a file
  whose name is already taken in the type folder it would move to.
- AC2: Run told to move, on the trial folder, the tool moves each file the list gives as moving into
  its type folder inside the trial folder, and leaves the files of no type, the folder, the hidden
  file and the same-name file where they were; afterwards the trial folder holds the same files, by
  name and content, as before, none lost, renamed or overwritten, and nothing outside it is changed.
- AC3: Given no folder, the tool organizes `~/Downloads`; given a folder, it organizes that folder
  and leaves `~/Downloads` as it was.
- AC4: AC1, AC2 and AC3 each hold on macOS and on Linux.
- AC5: The README says how to install the tool and how to use it, and a user following it on macOS
  or Linux gets the tool installed and runs both a plain run and a run told to move.
- AC6: Tests check the behaviour AC1, AC2 and AC3 name, and pass on macOS and on Linux.

## Tasks

- T2: The README of the tool, in place of the repository's README.md. Serves AC5.

  Completion criterion: a newcomer reading the README alone can tell what the tool is for, and can
  follow its steps to install it on macOS or Linux and to make a plain run and a run told to move,
  as the UX's scenes give them; checked by an AI that did not make it, reading it in a newcomer's
  place against the readme checklist.

  - [x] 1. Settle with the user how the tool is installed on macOS and on Linux. The orchestrator,
    with the user.
  - [ ] 2. Make the README from the UX of T1 and the answer of action 1, `README.md` as a readme
    work. turn.

## Next

Step 2 of /rn:up on t2.2: settle the points the README's result left, then step 3 on t2.2 again

## Open

- Result 0004 left B-7 of 0004-checklist-1.md: the reader should meet only what serves deciding and the first run, fuller use reached from Documentation; this falls short by the user's decision that no separate page is made and fuller use is written in the README itself (README.md:135-174).
- README.md:120,127 download the tool from https://github.com/lovaizu/playground/releases/latest/download/sort-downloads, a release asset no decision names, answering 404 until a release is published; README.md:137-138 point to the Releases page for changes; where the file is downloaded from is the user's to decide.
- README.md:1 drops the repository's one-line playground description, which the decision README says stays at its top.
- The LICENSE file holding the MIT text is made by no task yet; to be given a task once T2 is weighed.
