---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/22
stage: goal
signoff: none
artifact-language: English
conversation-language: Japanese
---

# Downloads folder organizer CLI

G1: A command-line tool that groups the files of the user's Downloads folder by type (Images, Documents, Archives and so on), so the user, who has so many files there that they cannot find the one they are looking for, finds it in its type's folder; it only moves files, never deletes, renames or overwrites one, and moves nothing until told to, so no file is lost.

## Acceptance criteria

- AC1: Run plainly on a Downloads folder, the tool shows, for each file directly in that folder, the type folder it would move the file to, and afterwards every file and folder in the Downloads folder is where it was, with the same name and contents.
- AC2: Run with the instruction to move, the tool moves each file directly in the Downloads folder whose extension one of the groups Images, Documents, Archives, Audio, Video and Installers holds into that group's folder inside the Downloads folder, making the folder where it is not there yet, the file keeping its name and contents.
- AC3: After any run, no file is deleted, renamed or overwritten: each file that was in the Downloads folder or in a folder under it is still there, or in a group's folder as AC2 says, with the same name and contents, and the files and folders that were in folders under the Downloads folder are where they were.
- AC4: Where a group's folder already holds a file of the same name as one to move there, that file stays where it is, and the run reports it by name, both when it only shows and when it moves.
- AC5: A file with no extension, or with one no group holds, stays where it is, and the run shows it in a list of files left in place.
- AC6: AC1 to AC5 hold on a folder of made-up files on macOS and on Linux.
- AC7: The README says how to install and how to use the tool, such that a reader following it alone on macOS or Linux installs the tool and runs it both to show and to move.
- AC8: The tool comes with tests that check AC1 to AC5 on folders of made-up files, and they pass on macOS and on Linux.

## Next

Step 6 of /rn:up on goal: find the point behind the feedback

## Open

- 前回の実行を取り消せるようにしてほしいです。取り消すと、前回移した各ファイルを元の場所へ戻します。これも判断基準とテストに入れてください。
