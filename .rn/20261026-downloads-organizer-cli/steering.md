---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/10
stage: design
signoff: none
artifact-language: English
conversation-language: Japanese
---

# CLI tool to organize the Downloads folder

G1: A command-line tool that moves the files directly in the Downloads folder into folders by kind, such as images, documents and archives, without deleting, renaming or overwriting any file, and can undo its last run, so that the user can easily find the file they want in a cluttered Downloads folder when they run it by hand.

## Acceptance criteria

- AC1: Told to move, the tool moves each file directly in the folder it is run on, the Downloads folder unless another is named, into the folder of its kind, such as images, documents and archives, and each file of no known kind, such as one with no extension or an unfamiliar one, into an Other folder.
- AC2: Files inside subfolders are not moved, and each subfolder is left where it was.
- AC3: After a run, every file that was there before is still there under its own name, and no file's content has changed.
- AC4: Where a file of the same name is already in the folder of its kind, the tool leaves the file where it is and reports it.
- AC5: Run without being told to move, the tool shows each file it would move and where, and moves nothing.
- AC6: The tool works on both macOS and Linux.
- AC7: A README says how to install the tool and how to use it.
- AC8: The repository's tests check AC1 to AC6 and AC9 by running the tool on a test folder of mixed files and subfolders, never on the real Downloads folder, and pass.
- AC9: Told to undo, the tool moves each file that its last run which moved files in that folder moved back to where it was; where a file of the same name is already there, it leaves the file in the folder of its kind and reports it; and it removes each folder of a kind that run made once that folder is empty, leaving each folder that was there before or still holds a file.

## Next

Step 5 of /rn:up on design: settle with the user shorter wordings for the decisions over 200 characters, then show the design sign-off

## Open

- rn.py proposal design stopped: decision 'Key results and their order' of t1.2 is 279 characters, over the 200 a sign-off line holds; also over 200: plan 'What shows it done' (414), t2.2 'Where the README sends the reader on' (241), 'What the README is checked against now' (278), 'The file's name and place' (201), 'How the README run ends' (208), t3.2 'Where the test rules are' (238)
- The README's install, Example, --help, commit history and docs/architecture.md link are to be checked for real once the tool is built (decisions 'What the README is checked against now' and 'How the README run ends' of t2.2); the build-stage plan must carry this
- The LICENSE file for the MIT license (decision 'License' of t2.2) is not yet made; the build-stage plan must carry it
