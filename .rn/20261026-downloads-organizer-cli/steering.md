---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/10
stage: plan
signoff: none
artifact-language: English
conversation-language: Japanese
---

# CLI tool to organize the Downloads folder

G1: A command-line tool that moves the files directly in the Downloads folder into folders by kind, such as images, documents and archives, without deleting, renaming or overwriting any file, so that the user can easily find the file they want in a cluttered Downloads folder when they run it by hand.

## Acceptance criteria

- AC1: Told to move, the tool moves each file directly in the folder it is run on, the Downloads folder unless another is named, into the folder of its kind, such as images, documents and archives, and each file of no known kind, such as one with no extension or an unfamiliar one, into an Other folder.
- AC2: Files inside subfolders are not moved, and each subfolder is left where it was.
- AC3: After a run, every file that was there before is still there under its own name, and no file's content has changed.
- AC4: Where a file of the same name is already in the folder of its kind, the tool leaves the file where it is and reports it.
- AC5: Run without being told to move, the tool shows each file it would move and where, and moves nothing.
- AC6: The tool works on both macOS and Linux.
- AC7: A README says how to install the tool and how to use it.
- AC8: The repository's tests check AC1 to AC6 by running the tool on a test folder of mixed files and subfolders, never on the real Downloads folder, and pass.

## Next

Step 3 of /rn:up on plan: write the plan again with the undo decisions; then step 5 on plan

## Open

- 最後の実行を取り消せるようにしてほしいです。取り消すと、その実行で移した各ファイルが元の場所へ戻るように。テストでもこれを確かめてください。
