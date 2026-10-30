---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/20
stage: architecture
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

- T4: The architecture document of the tool, `docs/architecture.md`. Serves AC1, AC2, AC3, AC4,
  AC5, AC6.

  Completion criterion: from the document alone, whoever builds the tool can tell the language and
  files it is made of, how it moves a file without ever overwriting one of the same name on macOS
  and on Linux, where its file sits for the README's download URL, and how its tests check AC1, AC2
  and AC3 and run on both macOS and Linux, each choice resting on the research's findings; checked
  by an AI that did not make it, reading it in the builder's place against the architecture
  checklist.

  - [x] 1. Research which language lets the tool be one file that runs on macOS and Linux with
    nothing else installed, how each OS moves a file without ever overwriting one of the same name,
    and where the tests can run on both OSes,
    `.rn/20261030-organize-downloads-cli/research.md` as a research work. turn.
  - [ ] 2. Make the architecture from the UX, the README and the research of action 1,
    `docs/architecture.md` as an architecture work. turn.

## Next

Step 2 of /rn:up on t4.2: settle how the README's steps are checked on macOS and Linux, then step 3 on t4.2 again

## Open

- docs/architecture.md:196-198 has the README checked by a person following its install and use steps on macOS and on Linux before each change is merged; no decision names who, and this session runs on Linux alone, so it would fall to the user, who chose not to check on their own Downloads.
- For learnings: in call 0008, turn's first user was refused reading usability.md by its read guard although turn.py first-user listed it in given, so F-3 of checklist.md came back left; the orchestrator checked it holds (usability.md line 3, version: 1, matches license.md line 6).
