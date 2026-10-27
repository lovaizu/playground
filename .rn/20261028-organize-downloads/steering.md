---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/17
stage: ux
signoff: none
artifact-language: English
conversation-language: Japanese
---

# Command-line tool to organize the Downloads folder

G1: A command-line tool, run on macOS or Linux, that sorts the files in the user's Downloads folder into folders by kind of file, so the user can find the file they need quickly instead of searching one long list, without ever losing a file or changing its name.

## Acceptance criteria

- AC1: Run with no option, the tool shows, for each file directly in Downloads, the folder it would move to, and moves nothing: after the run, every file and folder in Downloads is where it was.
- AC2: Run with the option that tells it to move, the tool moves each file directly in Downloads into a folder inside Downloads named for the file's kind in plain words, such as images or documents, every file of the same kind into the same folder, and each file to the folder the preview showed for it.
- AC3: After any run, every file that was in Downloads before it is still there, in Downloads or in a folder of its kind, with the same name and the same contents.
- AC4: When a file of the same name is already in the folder a file would move to, the tool leaves that file where it is, overwriting and renaming nothing, and shows that it left it, both in the preview and when moving.
- AC5: Every folder in Downloads before a run, and all that is inside it, is unchanged after the run, but for the files the tool moves into a folder of a kind or returns from it.
- AC6: The tool organizes once each time the user runs the command and leaves no process running after it ends.
- AC7: AC1 to AC6, AC8 and AC9 hold on macOS and on Linux.
- AC8: Run with the option that tells it to undo, the tool returns each file the last moving run moved back to where it was directly in Downloads, with the same name and the same contents.
- AC9: When undo would return a file and a file of the same name is already directly in Downloads, the tool leaves the file in its kind's folder, overwriting and renaming nothing, and shows that it left it.
- AC10: The repository's README says how to install the tool and how to use it to preview, to move and to undo.
- AC11: The repository's tests check preview only (AC1), moving (AC2), never deleting a file (AC3), leaving a same-name file and showing it (AC4, AC9), and undo (AC8), and they pass.

## Tasks

- T1: The UX of the tool, approved by the user. Serves AC1, AC2, AC4, AC8 and AC9.

  Completion criterion: the UX names each kind of file with the folder it goes to, and shows what the user types and sees in the preview, the moving run and undo, a same-name file left included; the user approves it at the ux sign-off.

  - [ ] 1. Settle with the user the kinds of file and the plain-word name of each kind's folder, and where a file of no listed kind goes. The orchestrator, with the user.
  - [ ] 2. Make the UX from the kinds and folder names settled in action 1, `.rn/20261028-organize-downloads/ux.md` as a ux work. turn.

- T2: The tool's README, saying how to use it to preview, to move and to undo. Serves AC10.

  Completion criterion: a reader who has only the README can tell from it what to type for the preview, the moving run and undo, and what each shows, as the UX of T1 gives them; the user approves it at the ux sign-off.

  - [ ] 1. Make the README from the UX of T1, `organize-downloads/README.md` as a readme work. turn.

## Next

Step 4 of /rn:up on T1: action 1, settle the kinds of file and their folder names with the user

## Open

None.
