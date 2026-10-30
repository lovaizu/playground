---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/21
stage: goal
signoff: none
artifact-language: English
conversation-language: Japanese
---

# Command-line tool to organize the Downloads folder

G1: The user can quickly find the file they want in their Downloads folder, which they cannot today: a command-line tool sorts the files there into one folder per kind of file, and only ever moves them, so nothing they downloaded is lost or changed.

## Acceptance criteria

- AC1: Run with no option, the tool shows, for each file directly in the folder, the kind's folder it would move to, or that it would stay and why, and moves nothing: every file and folder there is afterwards as it was before.
- AC2: Run with the move option, each file directly in the folder moves into the folder of its kind inside it, made where it is missing: Images, Documents, Videos, Audio, Archives, Installers or Code, told by the file's extension, and Others for a file whose extension is in none of them.
- AC3: Run with the move option, a file whose name is already in its kind's folder stays directly in the folder, and the tool shows that it was left because a file of the same name is there.
- AC4: Run with the move option, hidden files (names starting with a dot, such as `.DS_Store`), files a browser is still downloading (ending in `.crdownload`, `.part` or `.download`) and each subfolder with all it holds stay where they are.
- AC5: After any run, each file that was in the folder, at any depth, is there with the same name and contents, where it was or in its kind's folder, and no file is deleted, renamed or overwritten.
- AC6: Run with no folder named, the tool works on `~/Downloads`; run with a folder named, it works on that folder alone.
- AC7: AC1 to AC6 hold on macOS and on Linux, each checked there on a test folder holding files of each kind, a file whose name is already in its kind's folder, hidden files, unfinished downloads and a subfolder.
- AC8: The README says how to install the tool and how to use it, and following it on macOS or Linux installs the tool and runs it.
- AC9: The repository's tests check AC1 to AC6, and they pass on macOS and on Linux.

## Next

Step 5 of /rn:up on goal: stop at the goal sign-off

## Open

None.
