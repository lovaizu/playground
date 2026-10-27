---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/18
stage: goal
signoff: none
artifact-language: English
conversation-language: Japanese
---

# CLI tool to organize the Downloads folder

G1: A command-line tool, for macOS and Linux, that sorts the files in the Downloads folder into folders by type when the user runs it, so the user can find the file they are looking for quickly; it deletes nothing, it moves files only when the user tells it to, and when the user tells it to undo, it puts the files it moved in its last run that moved files back where they were.

## Acceptance criteria

- AC1: On macOS and on Linux, the tool run plainly on a Downloads folder holding files lists each file it would move with the folder it would go to, and the names, number and content of everything in Downloads are the same after the run as before.
- AC2: On macOS and on Linux, the tool told to move puts each file directly in Downloads into the folder named for its type, by the types and the extensions of each that the user approves at the ux sign-off.
- AC3: After the tool moves files, every file that was in Downloads before is still there, in Downloads or one of its folders, with the same content, and none is overwritten.
- AC4: After the tool moves files, each type's folder holds only files of that type, so a user who knows the type of the file they want finds it by opening that one folder.
- AC5: Where a file of the same name is already in the folder a file would go to, the tool leaves that file where it was, under its own name, and tells the user which file it left and why.
- AC6: The repository's README tells how to install the tool and how to use it, and a reader who follows it on macOS or Linux installs the tool and runs it plainly, told to move, and told to undo.
- AC7: The repository holds tests that check AC1 to AC5, AC8 and AC9, and they pass on macOS and on Linux.
- AC8: On macOS and on Linux, the tool told to undo puts each file it moved in its last run that moved files back where it was before that run, under the same name and with the same content.
- AC9: Where a file moved in that last run cannot be put back, because a file of the same name is now where it was or it is no longer where the run put it, the undo leaves that file as it is, deletes and overwrites nothing, puts back the other files, and tells the user which files it did not put back and why.

## Next

Step 5 of /rn:up on goal: show the goal sign-off again

## Open

None.
