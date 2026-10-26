# organize-downloads architecture

organize-downloads is one command in Python whose parts first work out what to move and only then,
when told, move it, writing down each move so that undo can move it back; what the user sees and
types is in the [README](../README.md).

- A run moves nothing unless the user adds `--apply`.

  The user sees every move before any is made.
- The tool only moves the user's files, into type folders it makes where missing and back: it
  overwrites, renames and deletes none of them.
- Nothing outside the organized folder changes, so what undo reads is kept inside it.
- The tool runs only when the user types it, and needs no package beyond its language's own
  runtime.

  Installing it then brings no other package for the user to keep up to date.

## User stories

- As the user, I want to install the tool from GitHub with pipx or uv, so that the
  organize-downloads command is on my PATH.
- As the user, I want to see which type folder each file in my Downloads folder, or in a folder I
  name, would go to, with nothing moved.
- As the user, I want to move those files into their type folders when I say so.
- As the user, I want to see what undo would put back of the last run that moved files, with
  nothing put back.
- As the user, I want to put those files back where they were when I say so.
- As the user, I want to read in the terminal which files are left in place and which extensions go
  to which folder.

## Architecture

### Logical view

![The components of organize-downloads and how they act on one another](architecture.svg)

- No component is done by an AI: each is code that does the same each time.
- To install, pipx or uv builds the tool from the repository and puts Command line on the PATH as
  the organize-downloads command.
- To show the moves, Command line takes the organized folder from Folder finder, the one given or
  else the user's Downloads, and prints the moves Organize planner makes from the files directly in
  that folder, each file's type folder taken from Type table and each file whose name is already
  taken there told apart as not to be moved.
- Type table also names the endings of files still being downloaded, which Organize planner leaves
  in place with folders and hidden files.
- With `--apply`, Command line hands those moves to Mover, which makes each missing type folder,
  moves each file, writes each move to Run record, and hands back the files it did not move, for
  Command line to print.
- To show what undo would put back, Command line prints the moves back that Undo planner makes from
  the last moves in Run record, each checked against the organized folder.
- With `undo --apply`, Command line hands those moves back to Mover, which moves each file back and
  then leaves Run record's file in place holding no moves, so undo typed again finds nothing.

  The tool deletes nothing in the organized folder, its own file included.
- Command line writes `--help` from Type table.

  The extensions the help shows are then always those the planner uses.
- Only Mover, and Run record as Mover writes to it, change the organized folder; Folder finder and
  the planners only read.

  A run without `--apply` then changes nothing, Run record included, by how the tool is made.
- Mover moves a file by giving it its new name as a hard link and then removing the old name, never
  by renaming over it.

  The link fails where the name is already taken, even by a file that came after the moves were
  worked out, such as a download that just finished, so no file of the user's is ever overwritten.
- Mover stops at the first link that fails for a reason other than the name being taken, and hands
  back that reason with the files it did not move, for Command line to print.

  Where the organized folder is on a file system that cannot make hard links, such as a USB drive
  formatted exFAT or FAT32, every link fails, so there the tool moves nothing and tells the user
  so, rather than move by a rename that could overwrite; a type folder it made stays, empty, as the
  tool deletes nothing.
- Run record writes its file by writing a new one beside it and renaming it over the old, the one
  file the tool replaces, being its own and not the user's.

  An interrupted write then leaves the last record whole, so undo still finds what it moved.
- Organizing and undo share one Mover.

  Both are moves that must overwrite nothing and that the user is told of in the same way.
- On Linux, Folder finder reads the download folder from the settings file of
  [xdg-user-dirs](https://www.freedesktop.org/wiki/Software/xdg-user-dirs/), the freedesktop.org
  tool that names the user's folders, rather than running its `xdg-user-dir` command.

  The tool then runs no other program.

### Physical view

```text
playground/                                 the repository
├── .github/workflows/organize-downloads.yml    <GitHub Actions workflow, YAML>
└── organize-downloads/
    ├── pyproject.toml                          <TOML, built with setuptools>
    ├── src/organize_downloads/
    │   ├── __init__.py                         <Python 3>
    │   ├── cli.py              Command line     <Python 3, argparse>
    │   ├── folder.py           Folder finder    <Python 3>
    │   ├── type_table.py       Type table       <Python 3>
    │   ├── organize.py         Organize planner <Python 3>
    │   ├── undo.py             Undo planner     <Python 3>
    │   ├── mover.py            Mover            <Python 3>
    │   └── record.py           Run record       <Python 3, json>
    └── tests/
        ├── test_<module>.py    one for each module above   <Python 3, unittest>
        └── test_stories.py     the user stories            <Python 3, unittest>

<organized folder>/
└── .organize-last-run          Run record's file   <JSON>
```

- At run time the tool depends on Python 3 and its standard library alone; to build it, pipx or uv
  fetches setuptools from PyPI.
- The user starts it by typing organize-downloads, the console script pyproject.toml names, which
  calls `main` in cli.py.

## Test

The repository has no rules for checking code or user stories, so organize-downloads sets its own
here.

- Each module is checked by tests in Python's standard unittest, each a Given, a When and a Then on
  a temporary folder.

  The tests then need nothing the tool does not, and never touch the user's own Downloads.
- The user stories are checked in test_stories.py by running the organize-downloads command end to
  end on a temporary folder.

  Only the installed command shows what the user meets, from the console script to the files moved.
- GitHub Actions runs all the tests on ubuntu-latest and macos-latest on every push, so the pull
  request shows that each holds on Linux and on macOS.
- The workflow installs the tool with `pipx install ./organize-downloads` and then runs
  `PYTHONPATH=src python3 -m unittest discover -s tests` in organize-downloads.

  The stories then run the command as pipx installs it for the user, and the module tests run the
  code as it is in src.
