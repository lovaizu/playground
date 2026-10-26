# Command-line tool to organize the Downloads folder

G1: A command-line tool for macOS and Linux that sorts the files directly in the user's Downloads folder into one folder per kind of file, because the folder now holds so many files that the user cannot find the one they are looking for, and sorted by kind they can; it never deletes, renames or overwrites a file.

## Acceptance criteria

- AC1: Run on a folder with no options, the tool prints one line for each file directly in it but those AC5 leaves out, saying the kind's folder the file would move to, or that it stays and why, and every file in the folder is left where and as it was.
- AC2: Run on a folder with the option that tells it to move, the tool moves each file directly in it that is of a known kind into that kind's folder inside it, made where missing, under the same name and with the same contents, and prints the same lines as AC1. The kinds' folders are Images (such as jpg, png, gif, heic, webp, svg), Documents (such as pdf, docx, xlsx, pptx, txt, md, csv), Archives (such as zip, tar, gz, 7z, rar), Installers (such as dmg, pkg, deb, rpm, AppImage), Audio (such as mp3, wav, m4a) and Videos (such as mp4, mov, mkv); the full list of extensions of each is settled in the design.
- AC3: A file of no known kind, such as one with no extension or an unfamiliar one, stays where it is, and its line says it stays because its kind is unknown.
- AC4: A file whose name its kind's folder already holds stays where it is under its own name, the file already in that folder is left as it was, and its line says it stays because the name is taken.
- AC5: A download still in progress, ending in .crdownload, .part or .download, and a hidden file, whose name begins with a dot, are never moved and have no line.
- AC6: The folders directly in the folder, and all they hold, are neither moved nor changed.
- AC7: After any run, every file that was in the folder or in a folder inside it is still in the folder or in a folder inside it, under the same name and with the same contents, and nothing has been added but the kinds' folders.
- AC8: Run with no folder given, the tool works on the user's Downloads folder, `~/Downloads`.
- AC9: Every criterion from AC1 to AC8 holds on Linux, shown by the tests run here on a test folder holding files of every case, and on macOS, shown by the user running the tool once on a test folder there.
- AC10: The README says how to install the tool and how to use it on macOS and Linux, and a user following it alone installs the tool, lists the planned moves and moves the files.
- AC11: The repository holds tests that check each criterion from AC1 to AC8, run by one command, and they pass on Linux.
