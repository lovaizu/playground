---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/16
stage: plan
signoff: plan
artifact-language: English
conversation-language: Japanese
---

# CLI tool to organize the Downloads folder

G1: A command-line tool, on Linux and macOS, that sorts the files directly in the user's ~/Downloads into folders by kind of file, such as Images, Documents, Videos, Music, Archives and Others, made inside Downloads, so that the user finds the file they want, where now too many files lie together to find it. It only moves files, never deleting, renaming or overwriting one, and moves nothing unless told to, so that no file of the user's is lost or changed by it.

## Acceptance criteria

- AC1: Run on a folder without being told to move, the tool lists each file directly in that folder with the folder it would move to, and afterwards every file and folder in it is where it was, with the same name and content.
- AC2: Run told to move, the tool moves each file directly in the folder into the folder of its kind inside it, making that folder where it is not there, a file of no kind the README lists going to Others; each file inside a subfolder stays where it was.
- AC3: A file whose name already exists in the folder it would move to is not moved, stays where it was, and is named in the tool's output as left for that reason; after any run, every file there was before is still there with the same name and content, no file overwritten.
- AC4: AC1 to AC3 hold on a trial folder holding at least images, documents, a file of no listed kind, a name already taken in a target folder and a subfolder with files in it, shown by automated tests and by real runs of the tool on Linux; run with no folder named, the tool works on ~/Downloads.
- AC5: The user installs the tool on their Mac as the README says and runs it once without being told to move, and it lists the files and the folders they would move to as AC1 says.
- AC6: The user runs the tool once without being told to move on their own ~/Downloads, and finds the folders it would sort the files into acceptable for finding a file.
- AC7: The README says how to install the tool and how to use it, the kinds and which files belong to each included, and a reader following it from a fresh clone installs the tool and runs it both without being told to move and told to move.

## Next

Step 5 of /rn:up on plan: wait for the user's answer, /rn:ty to approve, /rn:gm <feedback> to ask for a change.

## Open

None.
