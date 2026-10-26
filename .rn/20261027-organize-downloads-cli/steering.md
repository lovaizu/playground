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
- AC3: The tool tells a file's type by its extension and uses only these folders, which the user cannot change: Images (pictures), Documents (documents, PDFs, spreadsheets), Archives (zip and the like), Audio, Video, Installers (.dmg, .deb and the like), and Others for a file that fits none of them. Each file goes to the folder its last extension belongs to, matched without regard to case (report.tar.gz by gz): Images jpg jpeg png gif webp heic heif bmp tif tiff svg ico psd raw cr2 nef arw dng; Documents pdf doc docx xls xlsx ppt pptx odt ods odp rtf txt md csv tsv pages numbers key epub; Archives zip tar gz tgz bz2 xz zst 7z rar; Audio mp3 wav flac aac m4a ogg opus aif aiff wma mid midi; Video mp4 mov mkv avi webm m4v wmv flv mpg mpeg 3gp; Installers dmg pkg deb rpm appimage flatpak snap iso msi exe; Others every other file, one with no extension included.
- AC4: When a file of the same name is already in the folder a file would go to, the tool leaves that file where it is, overwrites and renames nothing, and tells the user it did not move it.
- AC5: The tool never moves or lists folders (the type folders included), symbolic links, whatever they point to, or other entries that are neither a plain file nor a folder, such as a named pipe; hidden files whose names begin with a dot (such as macOS's .DS_Store and .localized); or files still being downloaded (such as Chrome's .crdownload, Firefox's .part and Safari's .download), their endings matched without regard to case, so report.pdf.PART is one; and it does not look inside folders.
- AC6: With no folder given, the tool organizes the user's own Downloads folder: ~/Downloads on macOS, and on Linux the download folder the OS settings (xdg-user-dirs) name, such as ~/ダウンロード. Given another folder, it organizes that folder instead.
- AC7: AC1 to AC6 and AC8 to AC10 each hold on both macOS and Linux, shown on the pull request by the tool's tests, which GitHub Actions runs on both on every push.
- AC8: An undo command undoes the last run that moved files. Typed with nothing added, it only lists each file it would put back with the place it would go, and puts nothing back; told explicitly, such as with an option, it puts each file that run moved back where it was before that run, under the same name. A run that only lists leaves what undo would put back as it was. What undo reads is kept as a hidden file inside the organized folder, such as ~/Downloads/.organize-last-run, so nothing outside the organized folder changes. Once undo has put files back, undo typed again moves nothing and tells the user there is nothing to put back.
- AC9: When undo puts files back, it leaves in its type folder a file whose name is already taken at the place it would go back to, overwriting and renaming nothing, and skips a file no longer in its type folder, such as one the user moved or deleted since, without looking for it elsewhere; for each it tells the user it did not put it back, and it puts the other files back.
- AC10: The tool only moves files and never deletes anything: after any run, organizing or undo, each file that was in the organized folder or in its type folders before the run is still in one of them under the same name, and every folder is still there, a type folder that undo leaves empty included.
- AC11: A README says how to install the tool and how to use it.

## Tasks

- T4: The run with --apply, moving each listed file into its type folder. Serves AC2, AC4, AC7, AC10.

  Completion criterion: organize-downloads --apply moves each file the run with nothing added lists into its type folder inside the organized folder under the same name, making the folder where it is missing, and records the moves in the organized folder's hidden record file; it leaves a file whose name is taken in its type folder where it is and says so; where hard links cannot be made it moves nothing and says so; it deletes nothing and changes nothing outside the organized folder; the tests action 1 makes hold each of these and pass here on Linux, and in the GitHub Actions run of the push on macOS and Linux.

  Test: `uv run --no-cache --isolated --no-project --with ./organize-downloads python3 -m unittest discover -s organize-downloads/tests -t organize-downloads`

  - [x] 1. Make the tests of the run with --apply from AC2, AC4, AC10 and the architecture, and see them fail on what T3 built, `organize-downloads/tests` as a code work. turn.
  - [ ] 2. Make the moving from the architecture until every test passes, `organize-downloads` as a code work. turn.

- T5: The undo command, listing and putting back what the last run that moved files moved. Serves AC7, AC8, AC9, AC10.

  Completion criterion: organize-downloads undo lists each file the last run with --apply moved and where it would go back, changing nothing, and organize-downloads undo --apply puts each back under the same name, leaves in its type folder one whose name is taken where it would go, skips one no longer in its type folder, says so for each, leaves the type folders, and once done makes undo typed again move nothing and say so; a run that only lists leaves what undo puts back as it was; the tests action 1 makes hold each of these and pass here on Linux, and in the GitHub Actions run of the push on macOS and Linux.

  Test: `uv run --no-cache --isolated --no-project --with ./organize-downloads python3 -m unittest discover -s organize-downloads/tests -t organize-downloads`

  - [ ] 1. Make the tests of undo from AC8, AC9, AC10 and the architecture, and see them fail on what T4 built, `organize-downloads/tests` as a code work. turn.
  - [ ] 2. Make undo from the architecture until every test passes, `organize-downloads` as a code work. turn.

- T6: The README made again on the built tool. Serves AC11.

  Completion criterion: A newcomer following the README on the built tool, from installing it to a run that lists, a run with --apply and an undo, finds each step works and each output and statement as the tool gives it, --help included; an AI that did not write it finds this so, using the built tool in their place against the readme checklist.

  - [ ] 1. Make the README again from the built tool and the README of T1, `organize-downloads/README.md` as a readme work. turn.

## Next

Step 3 of /rn:up on t4.2: add tests/__init__.py to the work's paths, then send the answer to the run waiting

## Open

- turn asks for t4.2 (code B-5): whether tests/__init__.py is added to the work, so the full-disk error DISK_FULL is defined once beside NO_HARD_LINKS and WRITE_FAILED
