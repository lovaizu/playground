# sort-downloads

sort-downloads moves the files lying loose in your Downloads folder into folders by kind, such as
Images and Documents, always showing you each move before making it, and can move them all back.
It is a command you run in a terminal on Linux or macOS, for anyone whose Downloads holds so many
files that the one they want is hard to find.

## Example

Your `~/Downloads` holds a photo, two PDFs, a file of a kind the tool does not know, a folder, and
a few files the tool leaves alone; `Documents/report.pdf` is already there from before. Run the
tool with nothing after it, and it only shows what it would do:

```console
$ sort-downloads
In /Users/you/Downloads:
Would move:
  holiday.jpg -> Images/holiday.jpg
  invoice.pdf -> Documents/invoice.pdf
  notes.xyz -> Others/notes.xyz
Would leave:
  report.pdf: Documents/report.pdf already exists
  .DS_Store: hidden file
  movie.mp4.crdownload: download still running
Nothing was moved. Run again with --move to move these files.
```

Each file goes to the folder of its kind:

| Folder | Files ending in |
|---|---|
| Images | .jpg .jpeg .png .gif .heic .webp .svg .bmp .tif .tiff |
| Documents | .pdf .doc .docx .xls .xlsx .ppt .pptx .odt .ods .odp .pages .numbers .key .txt .md .rtf .csv .epub |
| Videos | .mp4 .mov .m4v .mkv .avi .webm .wmv |
| Music | .mp3 .m4a .aac .wav .flac .ogg .aiff |
| Archives | .zip .tar .gz .tgz .bz2 .xz .7z .rar .dmg |
| Others | any other ending, or none |

Capital letters count the same, so `IMG_0001.JPG` goes to Images. Some files stay where they are
and are listed under "Would leave", each with its reason:

- A file whose name is already taken in the folder it would go to.

  The tool never renames a file and never writes over one.

- A hidden file, whose name starts with a dot, such as `.DS_Store` or `.localized`.

  On a Mac, `.localized` is what makes Finder show Downloads in your own language.

- A download still running, whose name ends in `.crdownload` (Chrome) or `.part` (Firefox).

Folders, and the files inside them, are never moved. To make the moves, add `--move`:

```console
$ sort-downloads --move
In /Users/you/Downloads:
Moved:
  holiday.jpg -> Images/holiday.jpg
  invoice.pdf -> Documents/invoice.pdf
  notes.xyz -> Others/notes.xyz
Left:
  report.pdf: Documents/report.pdf already exists
  .DS_Store: hidden file
  movie.mp4.crdownload: download still running
```

The tool made `Images` and `Others`, as they were not there; `Documents` was. To sort a folder
other than `~/Downloads`, name it after the command, as in `sort-downloads --move ~/Desktop`.

To put things back as they were, add `--undo`. It undoes the last sort made with `--move`, in
whichever folder that sort was, so you name no folder with `--undo`; its first line says which
folder it is. Only that last sort can be undone. Like a sort, it only shows what it would do until
you add `--move` too. Suppose that, since the sort, you saved a new `notes.xyz` in Downloads:

```console
$ sort-downloads --undo
In /Users/you/Downloads:
Would move back:
  Images/holiday.jpg -> holiday.jpg
  Documents/invoice.pdf -> invoice.pdf
Would leave:
  Others/notes.xyz: notes.xyz already exists
Nothing was moved. Run again with --undo --move to move these files back.

$ sort-downloads --undo --move
In /Users/you/Downloads:
Moved back:
  Images/holiday.jpg -> holiday.jpg
  Documents/invoice.pdf -> invoice.pdf
Left:
  Others/notes.xyz: notes.xyz already exists
Removed empty folder:
  Images
```

`Others` still holds `notes.xyz`, so it stays, and `Documents` stays as it was there before the
sort. The tool removes only a folder that the undone sort made and that is now empty.

## Why sort-downloads

Sorting by hand means dragging each file into a folder you made yourself; sort-downloads does all
of them in one run, and you see the whole list before anything moves. Among the tools we tried in
October 2026, each lacks at least one of these:

- No file is renamed or written over, when sorting or when undoing.

  TidyMate and downloads-folder-organizer rename a file whose name is taken, and the latter's undo
  writes over a new file of the same name.

- Undoing is shown first, file by file, like sorting.

  TidyMate's undo shows only how many files it will move back; organize has no undo.

- It works with nothing to set up.

  organize needs you to write each kind and its folder in a settings file first.

## Requirements

- Python 3.9 or newer, run as `python3`.

  The tool is a Python program. Check with `python3 --version`. On a Mac where it is missing,
  `xcode-select --install` installs Apple's command line tools, which include `python3` and `git`;
  on Linux, install the `python3` package, such as with `sudo apt install python3`.

- Git, to get the tool.

## Installation

Get the tool and copy it into `~/.local/bin`:

```sh
git clone https://github.com/lovaizu/playground.git
mkdir -p ~/.local/bin
cp playground/sort-downloads/sort-downloads ~/.local/bin/
```

Then check that your terminal finds it:

```sh
command -v sort-downloads
```

If this prints nothing, `~/.local/bin` is not among the folders your terminal looks in. Add it,
then open a new terminal window:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc    # macOS
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc   # Linux
```

Now run `sort-downloads` as in Example. Once the tool is copied, the cloned `playground` folder can
be removed.

## Documentation

`sort-downloads --help` lists every option. What changed in each version is in the
[commit history](https://github.com/lovaizu/playground/commits/main/sort-downloads).

## Development

How the tool is put together and tested is in [the architecture](docs/architecture.md).

## License

No license has been chosen yet.
