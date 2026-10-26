---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/13
stage: design
signoff: none
artifact-language: English
conversation-language: Japanese
---

# Command-line tool to organize the Downloads folder

G1: A command-line tool for macOS and Linux that sorts the files directly in the user's Downloads folder into one folder per kind of file, because the folder now holds so many files that the user cannot find the one they are looking for, and sorted by kind they can; it never deletes, renames or overwrites a file, and the user can undo the last run that moved files.

## Acceptance criteria

- AC1: Run on a folder with no options, the tool prints one line for each file directly in it but those AC5 leaves out, saying the kind's folder the file would move to, or that it stays and why, and every file in the folder is left where and as it was.
- AC2: Run on a folder with the option that tells it to move, the tool moves each file directly in it that is of a known kind into that kind's folder inside it, made where missing, under the same name and with the same contents, and prints the same lines as AC1. The kinds' folders are Images (such as jpg, png, gif, heic, webp, svg), Documents (such as pdf, docx, xlsx, pptx, txt, md, csv), Archives (such as zip, tar, gz, 7z, rar), Installers (such as dmg, pkg, deb, rpm, AppImage), Audio (such as mp3, wav, m4a) and Videos (such as mp4, mov, mkv); the full list of extensions of each is settled in the design.
- AC3: A file of no known kind, such as one with no extension or an unfamiliar one, stays where it is, and its line says it stays because its kind is unknown.
- AC4: A file whose name its kind's folder already holds stays where it is under its own name, the file already in that folder is left as it was, and its line says it stays because the name is taken.
- AC5: A download still in progress, ending in .crdownload, .part or .download, and a hidden file, whose name begins with a dot, are never moved and have no line.
- AC6: The folders directly in the folder, and all they hold, are neither moved nor changed, apart from the files moved into the kinds' folders as AC2 says and the files moved back out of them and the kinds' folders removed as AC12 says.
- AC7: After any run, every file that was in the folder or in a folder inside it is still in the folder or in a folder inside it, under the same name and with the same contents, and nothing has been added but the kinds' folders.
- AC8: Run with no folder given, the tool works on the user's Downloads folder, `~/Downloads`.
- AC9: Every criterion from AC1 to AC8 and AC12 holds on Linux, shown by the tests run here on a test folder holding files of every case, and on macOS, shown by the user running the tool once on a test folder there.
- AC10: The README says how to install the tool and how to use it on macOS and Linux, and a user following it alone installs the tool, lists the planned moves, moves the files and undoes the move.
- AC11: The repository holds tests that check each criterion from AC1 to AC8 and AC12, run by one command, and they pass on Linux.
- AC12: Run on a folder with the option that tells it to undo, the tool returns each file that the last run moving files, as AC2 says, moved, to where it was, under the same name and with the same contents, prints one line for each such file saying it went back or that it stays and why, and removes each kind's folder that run made that is left empty; a folder that was there before that run, or that still holds anything, stays. A file whose old place now holds a file of the same name, or that is no longer where that run put it, stays where it is, and its line says why. The record of that run, which the undo reads, is kept outside the folder, in the user's own place for an application's data: `~/.local/state` on Linux, `~/Library/Application Support` on macOS.

## Next

Step 3 of /rn:up on t1.1: have turn return its result, .rn/20261026-organize-downloads/calls/0005-result.json, which rn.py proposal design needs; then step 5 on design

## Open

- rn.py proposal design stops: "turn has not returned the work t1.1: .rn/20261026-organize-downloads/calls/0005-result.json is not there". turn:up on t1.1, told by the user's decision "How t1.1 ends" to end with B-4, B-5 and B-8 waiting for the build stage, will not write the result: its flow opens a new round after each answer asking it to end, and it stopped saying the result must be written outside turn or turn.py fixed so such an answer closes the run. The orchestrator writes no line of what turn makes, so neither way is open to it.
- At the build stage, check B-4, B-5 and B-8 of the README checklist on organize-downloads/README.md, by a first user installing from its address and following its Example once the tool, docs/usage.md and CHANGELOG.md are on main and docs/architecture.md is made (decision "How t1.1 ends" of t1.1).
- At the build stage, make organize-downloads/docs/usage.md and organize-downloads/CHANGELOG.md with the tool (decision "License and the places of fuller use and of changes" of t1.1).
