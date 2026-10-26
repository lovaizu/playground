# tidy-downloads

tidy-downloads moves each file directly in your Downloads folder, or in another folder you name,
into a folder named for its kind, leaving in place one whose name is already taken there; it shows
every move before making it, never deletes, renames, overwrites or changes a file, and can put the
last move back. It is a command you type in a terminal: you then find a downloaded file by opening
the folder for its kind, such as Images, Documents or Archives, in place of searching one long
list. It is for people on macOS or Linux who type commands in a terminal and whose Downloads folder
fills up.

## Example

Your `~/Downloads` holds `beach.jpg`, `project.zip`, `invoice.pdf` and `notes`, a file with no
extension. It also holds a `Documents` folder you made earlier, which already has an `invoice.pdf`
in it.

First see what would move. Nothing is moved yet:

```console
$ tidy-downloads
beach.jpg -> Images/
project.zip -> Archives/
notes -> Other/
invoice.pdf stays: Documents/invoice.pdf already exists
Nothing was moved. Run tidy-downloads --move to move these files.
```

`Other` is the folder for a file with no extension, or with one tidy-downloads does not know.
`invoice.pdf` stays where it is, because moving it would overwrite the file of the same name.

Then move them:

```console
$ tidy-downloads --move
Moved beach.jpg -> Images/
Moved project.zip -> Archives/
Moved notes -> Other/
Left invoice.pdf: Documents/invoice.pdf already exists
```

tidy-downloads made `Images`, `Archives` and `Other`, since they were not there. To find the photo,
you now open `~/Downloads/Images`. Files already inside folders in `~/Downloads` stay where they
are, so `Documents` still holds just its own `invoice.pdf`.

If you do not like the result, put the last move back:

```console
$ tidy-downloads --undo
Moved back Images/beach.jpg
Moved back Archives/project.zip
Moved back Other/notes
Removed empty folders: Images, Archives, Other
```

The files are back in `~/Downloads` as they were before the move, and the folders the move made
are gone. Running `tidy-downloads --undo` a second time moves nothing, as only the last move is put
back, once.

To sort another folder, add its path at the end:

```sh
tidy-downloads ~/Desktop
tidy-downloads --move ~/Desktop
```

## Why tidy-downloads

- One command sorts the files directly in the folder, where by hand you decide on and drag each
  file in turn.
- You see where each file would go before any file is moved, where a script of `mv` commands moves
  them as it runs.
- A file is never moved onto another of the same name.

  A script of `mv` commands overwrites such a file unless told not to; tidy-downloads leaves the
  file where it is and says why.

- `tidy-downloads --undo` puts back every file of the last move in one command, where undo in a
  file manager takes back one drag at a time and `mv` has no undo.

## Requirements

- macOS or Linux, with a terminal.
- Python 3.

  tidy-downloads is a Python 3 script. If `python3 --version` prints a version, you have it. On
  macOS it may not be there; install it from https://www.python.org/downloads/ or in any way you
  like.

- curl, to fetch the file.

  It comes with macOS and most Linux systems; without it, a web browser does the same.

## Installation

Fetch the one file into `~/.local/bin` and make it runnable:

```sh
mkdir -p ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/lovaizu/playground/main/tidy-downloads -o ~/.local/bin/tidy-downloads
chmod +x ~/.local/bin/tidy-downloads
```

To use another folder on your PATH, put its path in place of `~/.local/bin`. Without curl, run the
`mkdir` line, open the address above in a browser, save what it shows as
`~/.local/bin/tidy-downloads`, and run the `chmod` line.

Check that your terminal finds it:

```sh
command -v tidy-downloads
```

If this prints nothing, `~/.local/bin` is not on your PATH. Add it with the line for your shell,
then open a new terminal and check again. To see your shell, run:

```sh
echo $SHELL
```

If it ends in `zsh`, the shell macOS starts:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

If it ends in `bash`, on Linux:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

If it ends in `bash`, on macOS:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bash_profile
```

Then run `tidy-downloads` and `tidy-downloads --move` as in the Example.

## Documentation

`tidy-downloads --help` shows every way to run it. What changed in each version is in the commit
history: https://github.com/lovaizu/playground/commits/main

## Development

Start at [docs/architecture.md](docs/architecture.md).

## License

tidy-downloads is under the MIT License.
