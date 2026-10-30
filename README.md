# sort-downloads

sort-downloads sorts the files of a piled-up Downloads folder by type into one folder per type
inside that same folder, showing first what it would move and never deleting, renaming or
overwriting a file. It is one command you type in a terminal on macOS or Linux, for anyone whose
Downloads folder has grown too long to find a file in, and afterwards you find a file by opening the
folder of its type.

## Example

Your Downloads folder holds `holiday.jpg`, `report.pdf`, `photos.zip`, `song.mp3`, `clip.mp4`,
`setup.dmg`, `notes`, `data.xyz`, a folder `old`, the hidden file `.DS_Store`, and `invoice.pdf`,
while a folder `Documents` inside it already holds a file named `invoice.pdf`.

First you run `sort-downloads` alone, which moves nothing and prints one line for each file, in name
order, saying where it would go or why it stays:

```
$ sort-downloads
Sorting /home/me/Downloads (nothing is moved without --move)
would move  clip.mp4     -> Video/
not moved   data.xyz     no type
would move  holiday.jpg  -> Images/
not moved   invoice.pdf  Documents/invoice.pdf already exists
not moved   notes        no type
would move  photos.zip   -> Archives/
would move  report.pdf   -> Documents/
would move  setup.dmg    -> Installers/
would move  song.mp3     -> Audio/
6 would move, 3 not moved. To move them, run: sort-downloads --move
```

The first line names the folder in full, `/Users/me/Downloads` on macOS. A file's type is told by
the end of its name after the last `.`, upper or lower case alike, as this table gives; a file whose
name has no such end, or one the table does not hold, is of no type and stays where it is:

| Folder     | Extensions                                                                      |
|------------|---------------------------------------------------------------------------------|
| Images     | jpg, jpeg, png, gif, heic, webp, bmp, tif, tiff, svg                            |
| Documents  | pdf, doc, docx, xls, xlsx, ppt, pptx, odt, ods, odp, rtf, txt, md, csv, pages, numbers, key |
| Archives   | zip, tar, gz, tgz, bz2, xz, 7z, rar                                             |
| Audio      | mp3, m4a, aac, wav, flac, ogg, aiff                                             |
| Video      | mp4, m4v, mov, mkv, avi, webm                                                   |
| Installers | dmg, pkg, deb, rpm, appimage                                                    |

Folders, such as `old`, and hidden files, whose names start with `.`, get no line and are never
moved. `invoice.pdf` stays because `Documents` already holds a file of that name.

The list is what you want, so you run it again with `--move`, which moves the files without asking
and prints what it did; each moved file keeps its name and content:

```
$ sort-downloads --move
Sorting /home/me/Downloads
moved       clip.mp4     -> Video/
not moved   data.xyz     no type
moved       holiday.jpg  -> Images/
not moved   invoice.pdf  Documents/invoice.pdf already exists
not moved   notes        no type
moved       photos.zip   -> Archives/
moved       report.pdf   -> Documents/
moved       setup.dmg    -> Installers/
moved       song.mp3     -> Audio/
6 moved, 3 not moved
```

Now you open the folder of the type you want, and the file is there:

```
$ ls ~/Downloads/Documents
invoice.pdf  report.pdf
```

When the list is not what you want, you stop after the first run, and nothing has moved.

## Why sort-downloads

- It sorts a whole folder in one command into six fixed type folders, with no rules for you to
  write first.

  By hand you drag files one at a time, and with an app that sorts by rules you set up each rule
  yourself before anything is sorted.

- It shows where every file would go before any moves, so you sort only once the list is what you
  want.

  By hand each file moves as you drop it, and an app that sorts by rules moves files as its rules
  match them.

- It sorts any other folder that piles up, such as your Desktop, the same way.

- It works the same on macOS and on Linux.

## Requirements

- macOS or Linux, with a terminal.

- `curl` or `wget`, to download the tool.

  macOS comes with `curl`, and most Linux systems come with one of the two.

- A folder on your PATH that you can write to; the steps below use `~/.local/bin`.

  Your PATH is the list of folders the terminal looks in for a command you type. To see whether
  `~/.local/bin` is in it, run `echo $PATH` and look for `/Users/me/.local/bin` on macOS or
  `/home/me/.local/bin` on Linux, `me` being your user name. Where it is not, add it with the line
  for your shell and open a new terminal:

  ```
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc    # macOS, whose shell is zsh
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc   # Linux, whose shell is most often bash
  ```

## Installation

Download the tool into `~/.local/bin` and make it executable:

```
mkdir -p ~/.local/bin
curl -fsSL -o ~/.local/bin/sort-downloads https://github.com/lovaizu/playground/releases/latest/download/sort-downloads
chmod +x ~/.local/bin/sort-downloads
```

On a Linux without `curl`, use this line in place of the second:

```
wget -qO ~/.local/bin/sort-downloads https://github.com/lovaizu/playground/releases/latest/download/sort-downloads
```

To update the tool, run the same commands again.

Then make your first run as in the example: `sort-downloads` to see the list, and
`sort-downloads --move` to sort.

## Documentation

Fuller use is written below, as the tool has no other manual; what changed in each version is
written on the [Releases page](https://github.com/lovaizu/playground/releases).

- To sort another folder, write it after the command, as `sort-downloads ~/Desktop` and then
  `sort-downloads --move ~/Desktop`.

  The type folders are made inside that folder, such as `~/Desktop/Images`, the lines are those of
  the example but for the folder named in them, the hint on the last line names the folder in full,
  as `To move them, run: sort-downloads --move /home/me/Desktop`, and `~/Downloads` is left as it
  was.

- A type folder is made by a run with `--move` the first time a file goes into it.

- Run again on a folder sorted before, the tool moves only the files that came in since, and lists
  again each file it left in place, with its reason.

- A file the tool cannot move gets the line `not moved NAME cannot move: REASON` and stays where it
  was, while the other files are still sorted.

  Where the name of its type folder is taken by a file, both runs give the line, as
  `cannot move: Images is not a folder`. Where the system refuses the move, as
  `cannot move: permission denied`, only the run with `--move` can find it out, so the run without
  it gives that file `would move`.

- When no file would move, the last line gives the counts alone, as `0 would move, 2 not moved`,
  and a folder with no file to give a line gets the one line
  `Nothing to sort in /home/me/Downloads`.

- When the tool cannot run, it says what is wrong, follows it with the line
  `Usage: sort-downloads [--move] [folder]`, and moves nothing:

  | You give                              | It prints                                       |
  |---------------------------------------|-------------------------------------------------|
  | a folder that is not there, or a file | `sort-downloads: /home/me/Dekstop is not a folder` |
  | an option it does not know            | `sort-downloads: unknown option --mvoe`         |
  | more than one folder                  | `sort-downloads: give one folder only`          |

  With no folder written and no `~/Downloads`, the message names `/home/me/Downloads`.

## Development

The documents on the tool's architecture and development are still to come.

## License

sort-downloads is released under the MIT License, which lets you use, copy, change and share it
freely, provided its copyright and license notice goes with each copy; the full text is in
[LICENSE](LICENSE).
