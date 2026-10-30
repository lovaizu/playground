# Command-line tool to organize the Downloads folder

G1: The user can quickly find the file they want in their Downloads folder, which they cannot today: a command-line tool sorts the files there into one folder per kind of file, only ever moves them, and can put back what its last move run moved, so nothing they downloaded is lost or changed.

## Acceptance criteria

- AC1: Run with no option, the tool shows, for each file directly in the folder, the kind's folder it would move to, or that it would stay and why, and moves nothing: every file and folder there is afterwards as it was before.
- AC2: Run with the move option, each file directly in the folder moves into the folder of its kind inside it, made where it is missing: Images, Documents, Videos, Audio, Archives, Installers or Code, told by the file's extension, and Others for a file whose extension is in none of them.
- AC3: Run with the move option, a file whose name is already in its kind's folder stays directly in the folder, and the tool shows that it was left because a file of the same name is there.
- AC4: Run with the move option, hidden files (names starting with a dot, such as `.DS_Store`), files a browser is still downloading (ending in `.crdownload`, `.part` or `.download`) and each subfolder with all it holds stay where they are.
- AC5: After any run, each file that was in the folder, at any depth, is there with the same name and contents, where it was or in its kind's folder, and no file is deleted, renamed or overwritten.
- AC6: Run with no folder named, the tool works on `~/Downloads`; run with a folder named, it works on that folder alone.
- AC7: AC1 to AC6, AC10 and AC11 hold on macOS and on Linux, each checked there on a test folder holding files of each kind, a file whose name is already in its kind's folder, hidden files, unfinished downloads and a subfolder, moved and then undone.
- AC8: The README says how to install the tool and how to use it, and following it on macOS or Linux installs the tool and runs it.
- AC9: The repository's tests check AC1 to AC6, AC10 and AC11, and they pass on macOS and on Linux.
- AC10: Run with the undo option, the tool puts each file the folder's last move run moved back directly in the folder, and removes each kind's folder that run made and that is then empty, keeping every folder that was there before the run or still holds anything; a file whose name is already directly in the folder, or that is no longer in its kind's folder, is not put back, and the tool shows that it was not put back because a file of the same name is there, or because it was not found.
- AC11: A move run adds nothing to the folder but the kinds' folders: the record that undoing reads is kept outside it, under `~/.local/state` on Linux and `~/Library/Application Support` on macOS.

## Tasks

- T1: The UX of the tool: who uses it, what they type for the preview, the move and the undo, and what it shows them for each case AC1 to AC6, AC10 and AC11 name. Serves AC1, AC2, AC3, AC4, AC5, AC6, AC10, AC11.

  Completion criterion: the user, reading it at the ux sign-off, can tell for each of those criteria the command they type and what the tool shows back, and whoever builds the tool takes the option names and messages from it without asking; every item of the ux checklist holds.

  - [ ] 1. Write the UX from the plan's goal and criteria, `.rn/20261030-organize-downloads-cli/ux.md` as a ux work. turn.

- T2: The tool's README, reached from the top README. Serves AC8.

  Completion criterion: a newcomer reading `organize-downloads/README.md`, after following the one line added to `README.md`, can tell whether the tool is for them, how to install it on macOS or Linux and how to preview, move and undo, each in the words the UX of T1 uses; every item of the readme checklist holds.

  - [ ] 1. Write the tool's README from the UX of T1, `organize-downloads/README.md` as a readme work. turn.
  - [ ] 2. Add to the top README one line linking to the tool's README of action 1, keeping the rest as it is, `README.md` as a readme work. turn.
