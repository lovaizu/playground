---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/15
stage: plan
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
- AC7: AC1 to AC6 each hold on both macOS and Linux, shown on the pull request by the tool's tests, which GitHub Actions runs on both on every push.

## Next

Step 2 of /rn:up on plan: hear the points the feedback opens on undo (where the record of the last run is kept, what counts as the last run, a same-named file at the original place, a file gone since the run, whether undo lists first, type folders left empty), then step 3 on plan and step 5 on the plan sign-off

## Open

- 3 点お願いします。(1) 計画を読んで思いましたが、直前の実行を元に戻せるようにしてください。直前の実行で動かした各ファイルを元の場所へ戻すコマンドです（以前の「元に戻す機能はなし」を変えます）。(2) インストールの仕方と使い方を書いた README を作ることを基準に入れてください。(3) ツールはファイルを動かすだけで、消すことは決してない、と基準に明記してください。
