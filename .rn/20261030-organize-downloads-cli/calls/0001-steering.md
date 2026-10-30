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
