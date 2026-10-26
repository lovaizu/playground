# organize-downloads

organize-downloads sorts the files in your Downloads folder into folders by type, but first only
shows where each file would go, moves them only when you say so, and can put back what it moved.
With a command you type in a terminal whenever you want to tidy up, you find the file you need in
Downloads right away; it is for anyone on macOS or Linux whose Downloads folder fills up with files
of every kind.

## Example

Your Downloads folder holds a photo, an invoice, an installer, a folder, macOS's hidden .DS_Store
and a file Chrome is still downloading:

```console
$ ls -A ~/Downloads
.DS_Store  Docker.dmg  Projects  holiday.jpg  invoice.pdf  report.pdf.crdownload
```

Type the command with nothing added. It lists where each file would go and moves nothing:

```console
$ organize-downloads
Would move 3 files in /Users/you/Downloads:
  Docker.dmg   -> Installers/
  holiday.jpg  -> Images/
  invoice.pdf  -> Documents/
Nothing was moved. To move these files, run: organize-downloads --apply
```

The folder, the hidden file and the file still downloading are not listed: the tool leaves
folders, files whose names begin with a dot and unfinished downloads where they are.

When the list is what you want, add `--apply`. The tool makes each type folder that is missing and
moves the files into it under the same names:

```console
$ organize-downloads --apply
Moved 3 files in /Users/you/Downloads:
  Docker.dmg   -> Installers/
  holiday.jpg  -> Images/
  invoice.pdf  -> Documents/
$ ls -A ~/Downloads
.DS_Store  Documents  Images  Installers  Projects  report.pdf.crdownload
```

To put them back, type `undo`. Like the first run, it only lists until you add `--apply`:

```console
$ organize-downloads undo
Would put back 3 files in /Users/you/Downloads:
  Installers/Docker.dmg  -> Docker.dmg
  Images/holiday.jpg     -> holiday.jpg
  Documents/invoice.pdf  -> invoice.pdf
Nothing was put back. To put these files back, run: organize-downloads undo --apply
$ organize-downloads undo --apply
Put back 3 files in /Users/you/Downloads:
  Installers/Docker.dmg  -> Docker.dmg
  Images/holiday.jpg     -> holiday.jpg
  Documents/invoice.pdf  -> invoice.pdf
```

Undo puts back the last run that moved files and leaves the type folders there, empty; typed again,
it tells you there is nothing to put back.

With no folder given, the tool organizes ~/Downloads on macOS, and on Linux the download folder your
system settings name, such as ~/ダウンロード. To organize another folder, give it last:

```console
$ organize-downloads ~/Desktop
$ organize-downloads --apply ~/Desktop
$ organize-downloads undo ~/Desktop
```

## Why organize-downloads

Sorting by hand means dragging each file to its folder yourself, and tools that watch the folder
move files as they arrive, by rules you write. organize-downloads differs from both:

- It shows every move before making any, and moves only when you add `--apply`.
- It puts back what its last run moved with `organize-downloads undo --apply`.
- It needs no rules: each file goes by its extension to one of seven fixed folders, Images,
  Documents, Archives, Audio, Video, Installers, or Others for a file that fits none of them.
- It never overwrites, renames or deletes a file.

  A file whose name is already taken in its type folder stays where it is, and the tool tells you
  it did not move it.

## Requirements

- macOS or Linux.
- Python 3.

  The tool is written in Python with its standard library alone; pipx, installed below, brings
  Python with it on macOS through Homebrew and on Linux through apt.
- pipx, or uv if you already use it.

  It installs the tool in a place of its own and puts the organize-downloads command on your PATH.
- git.

  pipx and uv fetch the tool from GitHub with it.

## Installation

On macOS, with [Homebrew](https://brew.sh):

```console
$ brew install pipx git
$ pipx ensurepath
```

On Debian or Ubuntu:

```console
$ sudo apt install pipx git
$ pipx ensurepath
```

Open a new terminal, so that it finds the commands pipx installs, and install the tool:

```console
$ pipx install "git+https://github.com/lovaizu/playground#subdirectory=organize-downloads"
```

If you use uv, install it with uv instead:

```console
$ uv tool install "git+https://github.com/lovaizu/playground#subdirectory=organize-downloads"
```

Then type the command with nothing added. It lists what it would move in your Downloads folder and
moves nothing; go on from there as in the [Example](#example):

```console
$ organize-downloads
```

## Documentation

For fuller use, such as what happens when a file of the same name is already in its type folder,
which files are left in place and which extensions go to which folder, run:

```console
$ organize-downloads --help
```

What changed is in the repository's
[commit history](https://github.com/lovaizu/playground/commits/main/organize-downloads).

## Development

How the tool is put together and tested is in [docs/architecture.md](docs/architecture.md).

## License

[MIT](LICENSE)
