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

Step 5 of /rn:up on design: show the design sign-off once rn is fixed for issue-1 (https://github.com/lovaizu/playground/issues/11); run rn.py proposal design again then

## Open

- Issues 1 and 2 were sent by the user's yes, but this environment's gh (/tmp/rn/20261026-acceptance-7vc7gbjm/bin/gh) put them at https://github.com/lovaizu/playground/issues/11 and /12, not lovaizu/ccpm, saying 'the trial keeps lovaizu/ccpm out of reach'
- rn.py decide refuses t1.2 (and so t2.2, t3.2): 'the steering holds no action T1.2 of turn's, which the work t1.2 is; ... or write the plan again with it'; the plan's 'What shows it done' is shortened, six decisions of t1.2, t2.2 and t3.2 are still over 200 characters; the design sign-off waits on rn's fix
- The README's install, Example, --help, commit history and docs/architecture.md link are to be checked for real once the tool is built (decisions 'What the README is checked against now' and 'How the README run ends' of t2.2); the build-stage plan must carry this
- The LICENSE file for the MIT license (decision 'License' of t2.2) is not yet made; the build-stage plan must carry it
