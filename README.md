# organize-downloads

organize-downloads sorts the files in a folder by their extension into six fixed kind folders,
`images`, `documents`, `archives`, `audio`, `video` and `installers`, under a rule built into the
tool that no file is ever deleted, renamed or overwritten. It is a command for the terminal on macOS
and Linux, for anyone whose Downloads folder has grown too full to find a file in: they find a file
by opening the one folder of its kind, with every file still there.

## Example

You try the tool on a test folder of your own before your real Downloads folder. Make one with a
few empty files and a subfolder:

```sh
mkdir -p ~/test-downloads/projects
touch ~/test-downloads/report.pdf ~/test-downloads/photo.JPG ~/test-downloads/setup.crdownload
```

Run with no option, the tool only shows what it would do. With no folder named it works on the
`Downloads` folder under your home; naming a folder as the last word makes it work there instead:

```sh
organize-downloads ~/test-downloads
```

```
Folder: /Users/me/test-downloads
would move  report.pdf  ->  documents/report.pdf
would move  photo.JPG  ->  images/photo.JPG
left  setup.crdownload  kind not known
left  projects/  subfolder
Nothing changed. Run with --move to make these moves.
```

On Linux the folder reads `/home/me/test-downloads`. `setup.crdownload`, like a file still being
downloaded, has an extension the tool does not sort, and a subfolder stays as it is with all it
holds; each file or subfolder left in place is shown with the reason. Add `--move` to make the
moves:

```sh
organize-downloads --move ~/test-downloads
```

```
Folder: /Users/me/test-downloads
moved  report.pdf  ->  documents/report.pdf
moved  photo.JPG  ->  images/photo.JPG
left  setup.crdownload  kind not known
left  projects/  subfolder
Moved 2 files. Run with --undo to see how to move them back.
```

The folder now holds `documents/report.pdf`, `images/photo.JPG`, `projects/` and
`setup.crdownload`. Say you then take the photo out of `images` to keep it in `projects`, and later
want the folder back as it was. `--undo` shows the moves back first:

```sh
mv ~/test-downloads/images/photo.JPG ~/test-downloads/projects/
organize-downloads --undo ~/test-downloads
```

```
Folder: /Users/me/test-downloads
would move back  documents/report.pdf  ->  report.pdf
not moved back  images/photo.JPG  no longer in images/
would remove empty folder  documents/
would remove empty folder  images/
Nothing changed. Run with --undo --move to make these moves back.
```

A kind folder is removed only when the last move run made it and it is empty once the files are
back. `--undo --move` makes the moves back:

```sh
organize-downloads --undo --move ~/test-downloads
```

```
Folder: /Users/me/test-downloads
moved back  documents/report.pdf  ->  report.pdf
not moved back  images/photo.JPG  no longer in images/
removed empty folder  documents/
removed empty folder  images/
Moved back 1 file. 1 file not moved back.
```

`report.pdf` is where it was, and `photo.JPG` stays in `projects/`, where you put it.

## Why organize-downloads

- Unlike sorting by hand or with rules you write, it shows every move before making it, and `--move` on a folder unchanged since then makes just those moves.

  Dragging files in a file manager or running a script shows nothing beforehand; a sort-by-type
  view changes only how the folder is shown, not where the files are. `--move` decides each file
  anew, so a file that arrives in between, such as a finished download, is moved too; run the
  preview again when the folder has changed.

- Unlike sorting by hand or by script, it can move back what its last run moved, and take away the kind folders that run made once they are empty.

  After sorting by hand, nothing remembers where each file was. What a run moved is kept under your
  home, so the folder itself gains no file of the tool's.

- Unlike a script of `mv` commands, it leaves a file in place, with the reason, where moving it would overwrite one of the same name.

  `mv` replaces that file without asking, and no option of organize-downloads turns the rule off.

- Unlike apps that sort by rules, it needs no setup.

  The six kind folders and the extensions in each are built in.

## Requirements

- macOS or Linux.
- Python 3.
- pipx, which installs a Python command-line tool in a place of its own and puts the command on
  your path.

  Install it as [pipx's installation guide](https://pipx.pypa.io/stable/how-to/install-pipx.html) says.

- Git, to get the tool from this repository.

## Installation

Get the repository and install the tool from it with pipx:

```sh
git clone https://github.com/lovaizu/playground.git
cd playground
pipx install .
```

`organize-downloads` then runs from any directory. Try it on a test folder as in the
[Example](#example); on your Downloads folder, run it with no folder named:

```sh
organize-downloads
organize-downloads --move
```

To remove the tool:

```sh
pipx uninstall organize-downloads
```

## Documentation

The full table of which extension goes to which kind folder, every reason a file is left in place
or not moved back, and where the tool keeps what the last run moved are in
[docs/ux.md](docs/ux.md). The tool has had no release yet, so no changes between versions are
written.

## Development

How the tool is built and tested is in [docs/architecture.md](docs/architecture.md).

## License

organize-downloads is under the MIT License.
