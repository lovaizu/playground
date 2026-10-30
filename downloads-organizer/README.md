# downloads-organizer

downloads-organizer groups the files of your Downloads folder into one folder per type, and shows you every move before it makes one, never deletes, renames or overwrites a file, and can move its last run's files back. It is a command you run in a terminal on macOS or Linux, for anyone whose Downloads folder holds so many files that they cannot find the one they are looking for: afterwards you open `Images`, `Documents`, `Archives`, `Audio`, `Video` or `Installers` and find it there.

## Example

Ana's Downloads folder holds `photo.jpg`, `report.pdf`, `setup.dmg`, `notes` and `data.xyz`, and a `Documents` folder she made earlier that already holds a `report.pdf`.

She first runs the command with nothing after it. It only shows what it would do, and moves nothing:

```
$ downloads-organizer
In /Users/ana/Downloads, a run with --move would move 2 files:

Images/
  photo.jpg
Installers/
  setup.dmg

Would not move 1 file, as its group's folder already holds a file of that name:
  report.pdf (Documents/report.pdf)

Left in place 2 files, as no group holds their extension:
  notes
  data.xyz

Nothing was moved. To move these files, run: downloads-organizer --move
```

The plan is what she wants, so she runs it with `--move`. It makes the `Images` and `Installers` folders, moves the same files the run before named, and leaves the same files where they are:

```
$ downloads-organizer --move
In /Users/ana/Downloads, moved 2 files:

Images/
  photo.jpg
Installers/
  setup.dmg

Did not move 1 file, as its group's folder already holds a file of that name:
  report.pdf (Documents/report.pdf)

Left in place 2 files, as no group holds their extension:
  notes
  data.xyz

To move these files back, run: downloads-organizer --undo
```

She opens `Downloads/Installers` and finds `setup.dmg` there.

Had the grouping not been what she wanted, one more command puts the files of that run back and removes the folders it made for them:

```
$ downloads-organizer --undo
In /Users/ana/Downloads, moved back 2 of the 2 files the last run with --move moved:
  photo.jpg
  setup.dmg

Removed 2 empty folders that run made:
  Images/
  Installers/
```

## Why downloads-organizer

- You see where every file would go before any moves, and `--move` then does exactly that.

  Sorting by hand in Finder or a file manager has no plan to look over first, and a tool that sorts files as they arrive moves them without showing you; here nothing moves that you did not see first.

- You take a whole grouping back with one command.

  By hand, putting hundreds of files back means finding and dragging each one again; `--undo` moves each file of the last `--move` run back and removes the group folders that run made, once they are empty.

- You are told about every file it leaves where it is, and why.

  Dragging files by hand, a file you skip or miss is not listed anywhere; here each file not moved is named with its reason, so you never look for a file in a folder it is not in.

- A file whose name is already taken stays where it is, named, instead of replacing the other or being renamed.

  Dropping a file into a folder by hand can replace a file of the same name once you confirm, and a tool that renames it, such as adding a number, leaves you a name you do not know; here no file is ever deleted, renamed or overwritten.

- You find a file by its type, without knowing its name or when it came.

  Each file whose extension a group holds goes to that group's folder, so a picture is in `Images` and an installer in `Installers`, which sorting by hand also gives, but here in one command.

## Requirements

- macOS or Linux, with a terminal.

- Python 3.9 or later.

  downloads-organizer is written in Python. Check with `python3 --version`.

- pipx.

  pipx installs the command where your terminal finds it, apart from the rest of your Python. Install it with `brew install pipx` on macOS, or `sudo apt install pipx` on Debian or Ubuntu (`sudo dnf install pipx` on Fedora), then run `pipx ensurepath` and open a new terminal.

## Installation

Install the command:

```
pipx install "git+https://github.com/lovaizu/playground.git#subdirectory=downloads-organizer"
```

Then, in a new terminal, run it with nothing after it to see what it would do with `~/Downloads`; nothing is moved:

```
downloads-organizer
```

When what it shows is what you want, move the files, and undo that run if you change your mind, as in the [example](#example):

```
downloads-organizer --move
downloads-organizer --undo
```

To work on another folder, name it after the command, as in `downloads-organizer ~/Desktop --move`.

## Documentation

`downloads-organizer --help` prints each way to run it and the extensions each group holds. What changed in each version is in the [history of this folder](https://github.com/lovaizu/playground/commits/main/downloads-organizer).

## Development

How the code is laid out, how to run its tests and where its architecture is written are in [docs/development.md](docs/development.md).

## License

MIT; see [LICENSE](LICENSE).
