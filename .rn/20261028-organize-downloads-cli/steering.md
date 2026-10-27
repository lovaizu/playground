---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/18
stage: goal
signoff: none
artifact-language: English
conversation-language: Japanese
---

# CLI tool to organize the Downloads folder

G1: A command-line tool, for macOS and Linux, that sorts the files in the Downloads folder into folders by type when the user runs it, so the user can find the file they are looking for quickly; it deletes nothing, and it moves files only when the user tells it to.

## Acceptance criteria

- AC1: On macOS and on Linux, the tool run plainly on a Downloads folder holding files lists each file it would move with the folder it would go to, and the names, number and content of everything in Downloads are the same after the run as before.
- AC2: On macOS and on Linux, the tool told to move puts each file directly in Downloads into the folder named for its type, by the types and the extensions of each that the user approves at the ux sign-off.
- AC3: After the tool moves files, every file that was in Downloads before is still there, in Downloads or one of its folders, with the same content, and none is overwritten.
- AC4: After the tool moves files, each type's folder holds only files of that type, so a user who knows the type of the file they want finds it by opening that one folder.
- AC5: Where a file of the same name is already in the folder a file would go to, the tool leaves that file where it was, under its own name, and tells the user which file it left and why.
- AC6: The repository's README tells how to install the tool and how to use it, and a reader who follows it on macOS or Linux installs the tool and runs it both plainly and told to move.
- AC7: The repository holds tests that check AC1 to AC5, and they pass on macOS and on Linux.

## Next

Step 6 of /rn:up on goal: find the point behind the feedback

## Open

- 最後の実行を取り消せるようにしてほしい。指示すると、前回動かした各ファイルを元の場所へ戻す。これも完成の目安とテストに入れて。
