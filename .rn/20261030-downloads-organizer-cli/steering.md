---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/22
stage: ux
signoff: none
artifact-language: English
conversation-language: Japanese
---

# Downloads folder organizer CLI

G1: A command-line tool that groups the files of the user's Downloads folder by type (Images, Documents, Archives and so on), so the user, who has so many files there that they cannot find the one they are looking for, finds it in its type's folder; it only moves files, never deletes, renames or overwrites one, moves nothing until told to, and can undo its last run that moved files, moving each of those files back, so no file is lost.

## Acceptance criteria

- AC1: Run plainly on a Downloads folder, the tool shows, for each file directly in that folder, the type folder it would move the file to, and afterwards every file and folder in the Downloads folder is where it was, with the same name and contents.
- AC2: Run with the instruction to move, the tool moves each file directly in the Downloads folder whose extension one of the groups Images, Documents, Archives, Audio, Video and Installers holds into that group's folder inside the Downloads folder, making the folder where it is not there yet, the file keeping its name and contents.
- AC3: After any run, no file is deleted, renamed or overwritten: each file that was in the Downloads folder or in a folder under it is still there, or moved as AC2 or AC9 says, with the same name and contents, and every other file and folder in folders under the Downloads folder is where it was, but for the group folders AC11 says an undo removes.
- AC4: Where a group's folder already holds a file of the same name as one to move there, that file stays where it is, and the run reports it by name, both when it only shows and when it moves.
- AC5: A file with no extension, or with one no group holds, stays where it is, and the run shows it in a list of files left in place.
- AC6: AC1 to AC5 and AC9 to AC12 hold on a folder of made-up files on macOS and on Linux.
- AC7: The README says how to install and how to use the tool, such that a reader following it alone on macOS or Linux installs the tool and runs it to show, to move and to undo.
- AC8: The tool comes with tests that check AC1 to AC5 and AC9 to AC12 on folders of made-up files, and they pass on macOS and on Linux.
- AC9: Run with the instruction to undo, the tool moves each file that the last run with the instruction to move moved back to where it was directly in the Downloads folder, the file keeping its name and contents; no run before that one is undone.
- AC10: Where a file the undone run moved cannot go back, because a file of the same name is now directly in the Downloads folder or the file is no longer in its group's folder, that file stays where it is and the undo reports it by name, and every other file still goes back.
- AC11: After an undo, each group folder that the undone run made and that is empty once the files are back is gone; a group folder that holds anything, or that was there before that run, stays as it is.
- AC12: Run with the instruction to undo where no run with the instruction to move has been made since the last undo, or none at all, the tool moves nothing and says there is no run to undo.


## Tasks

- T3: The UX of T1 made again from the choices the user confirmed on it: the extensions of each group, the command name and instructions, the folder worked on, and the case of extensions and names. Serves AC1, AC2, AC4, AC5, AC9, AC10, AC11, AC12.

  Completion criterion: read against the criteria it serves, each of them shows in a scene of the UX as what the user types and what the tool shows back, each confirmed choice is in it as decided, and the user approves it at the ux sign-off.

  - [ ] 1. Write the UX again from the goal, the criteria and the choices the user confirmed on it, `.rn/20261030-downloads-organizer-cli/ux.md` as a ux work. turn.

- T4: The README of T2 made again from the UX of T3 and the choices the user confirmed on it: how the tool is installed, its licence, the development document it links to, and what --help shows. Serves AC7.

  Completion criterion: a reader with only the README, on macOS or Linux, finds in it each step to install the tool and to run it to show, to move and to undo, each command and what it shows matching the UX of T3, each confirmed choice in it as decided, and the user approves it at the ux sign-off.

  - [ ] 1. Write the README again from the UX of T3 and the choices the user confirmed on it, `downloads-organizer/README.md` as a readme work. turn.

## Next

Step 5 of /rn:up on ux: stop at the ux sign-off, once rn can close t1.1 and t2.1

## Open

- rn.py proposal ux stops: turn has not returned t1.1 (call 0006) or t2.1 (call 0009), the calls the decisions confirmed after their results opened; rn.py ccs t1.1 stops as the steering holds no action T1.1, ticked done by the orchestrator before the work was made again from those decisions (orchestrator.md step 3 says to make it again first), and a task T1 cannot be written again under its ID; T3 and T4, added to make both again, do not close t1.1 or t2.1, and the decisions are not carried to t3.1 (call 0010 holds none of them). No step of rn goes on from here.
- To carry into the plan at the build stage: the build makes downloads-organizer/LICENSE (MIT, its copyright holder still to be asked) and downloads-organizer/docs/development.md before the README is merged, adds the one line in the top README.md pointing to downloads-organizer/README.md, and checks every README link leads to a file
