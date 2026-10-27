---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/16
stage: design
signoff: none
artifact-language: English
conversation-language: Japanese
---

# CLI tool to organize the Downloads folder

G1: A command-line tool, on Linux and macOS, that sorts the files directly in the user's ~/Downloads into folders by kind of file, such as Images, Documents, Videos, Music, Archives and Others, made inside Downloads, so that the user finds the file they want, where now too many files lie together to find it, and that can undo its last sort, moving each file it moved back to where it was, so that Downloads can be put back as it was. It only moves files, never deleting, renaming or overwriting one, the one thing it removes being a folder of a kind it made that undoing has left empty, and moves nothing unless told to, so that no file of the user's is lost or changed by it.

## Acceptance criteria

- AC1: Run on a folder without being told to move, the tool lists each file directly in that folder with the folder it would move to, and afterwards every file and folder in it is where it was, with the same name and content.
- AC2: Run told to move, the tool moves each file directly in the folder into the folder of its kind inside it, making that folder where it is not there, a file of no kind the README lists going to Others; each file inside a subfolder stays where it was.
- AC3: A file whose name already exists in the folder it would move to is not moved, stays where it was, and is named in the tool's output as left for that reason; after any run, every file there was before is still there with the same name and content, no file overwritten.
- AC4: AC1 to AC3 and AC8 hold on a trial folder holding at least images, documents, a file of no listed kind, a name already taken in a target folder, a subfolder with files in it, and, after a sort, a new file of the same name as one the sort moved, put where that one was; shown by automated tests and by real runs of the tool on Linux; run with no folder named, the tool works on ~/Downloads.
- AC5: The user installs the tool on their Mac as the README says and runs it once without being told to move, and it lists the files and the folders they would move to as AC1 says.
- AC6: The user runs the tool once without being told to move on their own ~/Downloads, and finds the folders it would sort the files into acceptable for finding a file.
- AC7: The README says how to install the tool and how to use it, undoing included, the kinds and which files belong to each included, and a reader following it from a fresh clone installs the tool and runs it to sort and to undo, each both without being told to move and told to move.
- AC8: Run to undo without being told to move, the tool lists each file the last sort moved, the sort being the last run told to move that was not to undo, with the place it would go back to, and afterwards every file and folder is where it was; run to undo and told to move, it moves each file the last sort moved back to where it was, one by one, and removes each folder that sort made that is then empty; a file whose old place now holds a file of the same name is not moved back, stays where it is, and is named in the tool's output as left for that reason; a folder that was there before that sort, or that still holds anything, is not removed.

## Tasks

- T2: The architecture, `sort-downloads/docs/architecture.md`, holding how the tool is put together to do what the README says, the record of the last sort that undo reads included, and how each part and AC1 to AC3 and AC8 are checked by automated tests and real runs on Linux. Serves AC1, AC2, AC3, AC4 and AC8.

  Completion criterion: the user, reading it at the design sign-off with the README, finds each use the README shows taken on by a part, the language and way of installing action 2 of T1 settled used, and a check named for each of AC1 to AC3 and AC8 on the trial folder AC4 names, and approves it as how the tool is built.

  - [ ] 1. Make the architecture from the README of T1 and the research result of T1's action 1, `sort-downloads/docs/architecture.md` as an architecture work. turn.

## Next

Step 4 of /rn:up on T1: weigh what it brought; AC2 written again for the files left unsorted

## Open

None.
