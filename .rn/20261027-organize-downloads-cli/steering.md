---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/15
stage: build
signoff: none
artifact-language: English
conversation-language: Japanese
---

# CLI tool to organize the Downloads folder

G1: The user wants to find the file they need in their Downloads folder right away; for that, a command they type in a terminal whenever they want to organize, on macOS or Linux, sorts the files there into folders by file type.

## Acceptance criteria

- AC1: Typed in a terminal as one command with nothing added, the tool only lists each file it would move with the type folder it would go to, and moves nothing: every file and folder in the organized folder is as it was before the run. Nothing makes the tool run on its own, such as on a schedule.
- AC2: Told explicitly to move, such as with an option, the tool moves each file it lists into that type folder inside the organized folder, such as ~/Downloads/Images, making the folder where it is missing; each moved file keeps its name, and nothing outside the organized folder changes.
- AC3: The tool tells a file's type by its extension and uses only these folders, which the user cannot change: Images (pictures), Documents (documents, PDFs, spreadsheets), Archives (zip and the like), Audio, Video, Installers (.dmg, .deb and the like), and Others for a file that fits none of them. Each file goes to the folder its extension belongs to in the list of extensions per folder, which is still to be settled.
- AC4: When a file of the same name is already in the folder a file would go to, the tool leaves that file where it is, overwrites and renames nothing, and tells the user it did not move it.
- AC5: The tool never moves folders (the type folders included), hidden files whose names begin with a dot (such as macOS's .DS_Store and .localized), or files still being downloaded (such as Chrome's .crdownload, Firefox's .part and Safari's .download), and does not look inside folders.
- AC6: With no folder given, the tool organizes the user's own Downloads folder: ~/Downloads on macOS, and on Linux the download folder the OS settings (xdg-user-dirs) name, such as ~/ダウンロード. Given another folder, it organizes that folder instead.
- AC7: AC1 to AC6 and AC8 to AC10 each hold on both macOS and Linux, shown on the pull request by the tool's tests, which GitHub Actions runs on both on every push.
- AC8: An undo command undoes the last run that moved files. Typed with nothing added, it only lists each file it would put back with the place it would go, and puts nothing back; told explicitly, such as with an option, it puts each file that run moved back where it was before that run, under the same name. A run that only lists leaves what undo would put back as it was. What undo reads is kept as a hidden file inside the organized folder, such as ~/Downloads/.organize-last-run, so nothing outside the organized folder changes. Once undo has put files back, undo typed again moves nothing and tells the user there is nothing to put back.
- AC9: When undo puts files back, it leaves in its type folder a file whose name is already taken at the place it would go back to, overwriting and renaming nothing, and skips a file no longer in its type folder, such as one the user moved or deleted since, without looking for it elsewhere; for each it tells the user it did not put it back, and it puts the other files back.
- AC10: The tool only moves files and never deletes anything: after any run, organizing or undo, each file that was in the organized folder or in its type folders before the run is still in one of them under the same name, and every folder is still there, a type folder that undo leaves empty included.
- AC11: A README says how to install the tool and how to use it.

## Next

Step 10 of /rn:up on plan: make the tasks that build the finished work

## Open

None.
