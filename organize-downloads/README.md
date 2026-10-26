# organize-downloads

organize-downloads sorts the files lying directly in a folder into one folder per kind of file,
chosen by each file's extension; run without moving anything, it lists every move it would make,
and when it moves, it never deletes, renames or overwrites a file and can put back what its last
move moved. It is a command-line tool for macOS and Linux, for anyone whose Downloads folder holds
so many files that they cannot find the one they want, and who would find it in a folder of its
kind.

## Example

Your Downloads folder holds these files and folders, `Documents` already there with a
`budget.xlsx` of its own:

```
~/Downloads/
├── .DS_Store
├── budget.xlsx
├── Documents/
│   └── budget.xlsx
├── holiday.jpg
├── notes
├── Projects/
├── report.pdf
├── setup.dmg
└── talk.mp4.part
```

Run with no option, the tool only lists what it would do, one line per file in name order, and
moves nothing:

```
$ organize-downloads
budget.xlsx: stays, Documents/budget.xlsx already exists
holiday.jpg -> Images/
notes: stays, unknown kind
report.pdf -> Documents/
setup.dmg -> Installers/
```

`.DS_Store` has no line because hidden files, whose names begin with a dot, are never moved, and
`talk.mp4.part` has none because a download still in progress, ending in `.crdownload`, `.part` or
`.download`, is never moved either. The folder `Projects`, and every folder already there with all
it holds, is left as it is, apart from the files moved into a kind's folder such as `Documents`
and moved back out of it by `--undo`.

Run with `--move`, the tool makes the moves it listed, making `Images` and `Installers` as they are
missing, and prints the same lines:

```
$ organize-downloads --move
budget.xlsx: stays, Documents/budget.xlsx already exists
holiday.jpg -> Images/
notes: stays, unknown kind
report.pdf -> Documents/
setup.dmg -> Installers/
```

The folder then holds:

```
~/Downloads/
├── .DS_Store
├── budget.xlsx
├── Documents/
│   ├── budget.xlsx
│   └── report.pdf
├── Images/
│   └── holiday.jpg
├── Installers/
│   └── setup.dmg
├── notes
├── Projects/
└── talk.mp4.part
```

Run with `--undo`, the tool puts back each file the last `--move` on that folder moved, and removes
each folder that move made and that is now empty, so `Images` and `Installers` go and `Documents`,
there before, stays:

```
$ organize-downloads --undo
holiday.jpg: back from Images/
report.pdf: back from Documents/
setup.dmg: back from Installers/
```

The folder is then again as it was at first.

A file that cannot go back, because a file of its name is now in its old place or it is no longer
in the folder the move put it in, stays where it is, and its line says which.

With no folder given, the tool works on `~/Downloads`; give a folder after the options to work on
another, such as `organize-downloads --move ~/Desktop`.

A file goes to the folder of its kind by its extension, the part of its name after the last dot,
in capitals or small letters alike; so `archive.tar.gz` goes to `Archives`, and a file whose
extension is not in this table, or that has none, stays:

| Folder     | Extensions                                                                         |
|------------|------------------------------------------------------------------------------------|
| Images     | jpg, jpeg, png, gif, heic, heif, webp, svg, bmp, tif, tiff                          |
| Documents  | pdf, doc, docx, xls, xlsx, ppt, pptx, odt, ods, odp, rtf, txt, md, csv, pages, numbers, key |
| Archives   | zip, tar, gz, tgz, bz2, xz, 7z, rar                                                 |
| Installers | dmg, pkg, deb, rpm, AppImage                                                        |
| Audio      | mp3, wav, m4a, aac, flac, ogg, opus, aiff                                           |
| Videos     | mp4, mov, mkv, avi, webm, m4v                                                       |

## Why organize-downloads

Each other way to sort a Downloads folder leaves you work that this tool does for you.

- By hand, you make each folder and drag each file into it yourself.

- Sorting by kind in a file manager, such as Finder on macOS or Files on Linux, orders only the
  view, and the files stay together in the one folder.

- An organizer that sorts by rules asks you to write the rules before it moves anything; this tool
  comes with its kinds, in the table above.

## Requirements

- Python 3.8 or later, run by the command `python3`.

  The tool is a Python program. `python3 --version` tells you whether you have it; most Linux
  systems do, and on macOS, if it is missing, running `python3` once offers to install it, or you
  can get it from https://www.python.org/downloads/.

- The command `curl`, to download the tool.

  macOS has it; on a Linux system without it, install it with the system's package manager, such
  as `sudo apt install curl`.

- The folder `~/.local/bin` in your `PATH`, so that your shell finds the tool by its name.

  `echo "$PATH"` shows whether it is there. If not, add this line to `~/.zshrc` (macOS) or
  `~/.bashrc` (Linux) and open a new terminal:

  ```
  export PATH="$HOME/.local/bin:$PATH"
  ```

## Installation

Download the tool into `~/.local/bin` and make it runnable:

```
mkdir -p ~/.local/bin
curl -fsSL -o ~/.local/bin/organize-downloads https://raw.githubusercontent.com/lovaizu/playground/main/organize-downloads/organize-downloads
chmod +x ~/.local/bin/organize-downloads
```

`organize-downloads --help` then prints how to run it. Your first use is the three runs of the
Example on your own `~/Downloads`: first with no option, then `--move`, and `--undo` if you want
the files back.

## Documentation

- Every case the tool meets, and what it does in it, is in [docs/usage.md](docs/usage.md).

- What changed in each version is in [CHANGELOG.md](CHANGELOG.md).

## Development

How the tool is made and how its tests are run is in [docs/architecture.md](docs/architecture.md).

## License

MIT; see [LICENSE](LICENSE).
