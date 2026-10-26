# organize-downloads architecture

organize-downloads is one Python command that, on each run, plans every move from what it reads in
the folder or in the record, and hands each move it makes to the one part that changes the folder;
it gives the UX in [docs/ux.md](ux.md), whose words, such as kind folder, move run and record, are
defined under [Scenes](ux.md#scenes).

- The rule that no run deletes, renames or overwrites a file is held by the one part that changes the folder, whatever the parts before it hand it.
- A preview run and a move run decide each file by the same plan, so on a folder unchanged in between a move run makes no move but those the preview showed.
- The tool writes nothing in the folder but the files it moves and the kind folders; what it keeps is under the user's home.
- Each move a move run makes is in the record before it is made, so `--undo` reaches every move of a run, even one that stopped part way.

## User stories

- As the user, I want to see what organizing my Downloads folder, or one I name, would move where, with nothing changed.
- As the user, I want to move the files of that folder into their kind folders.
- As the user, I want to see what the last move run on that folder would move back, with nothing changed.
- As the user, I want to move back what the last move run on that folder moved.

## Architecture

### Logical view

![Logical view](architecture.svg)

- In a preview run, the Command asks the Planner for the plan and prints it; in a move run, it then hands each planned move to the Mover in turn, having the Record store keep the move, and the kind folder the Mover is to make for it, before the Mover makes it, and drop it again if the Mover refuses it.

  The move run is given no plan of its own, which is what makes it match the preview. Kept before it is made, every move of a run stopped at any point is in the record; one kept but not made shows under `--undo` as not moved back, and loses no file.

- In an undo preview run, the Command asks the Undo planner for the plan back, which the Undo planner makes from the Record store's moves of the last move run and from what is now in the folder, and prints it; in an undo move run, it then hands each move back to the Mover, has the Record store drop each one made, and last hands the Mover each kind folder to remove.

  The files not moved back stay in the record, as [Undoing](ux.md#undoing) asks.

- The Mover moves a file by making a hard link to it at its new name, which the system refuses when that name is taken, and only then taking away the old name; it removes a kind folder by a call the system refuses when the folder holds anything.

  A check made before the move would leave a moment in which another program, such as a browser finishing a download, could put a file at that name; the system's own refusal leaves none. A run stopped between making the hard link and taking away the old name keeps the file under both names, which `--undo` shows as not moved back, as the move is already in the record. A move refused because the name is taken shows `name taken in <kind>/` or `<file> is now in the folder`, as in the UX.

- A move the system refuses for another reason, such as no permission, or no hard links on the folder's file system, as on FAT, exFAT and many network shares, leaves the file in place, shown with the system's message as the reason, and the Mover has no other way of moving.

  The UX names no such reason, and leaving the file is what the first rule asks. Any other way of moving would leave the moment above in which a file could be overwritten, so on a file system without hard links a move run moves nothing, which the preview cannot show, as it changes nothing.

- The Record store begins a move run's record anew, empty, before the run's first move, and writes each record whole to a new file that then takes the old one's place in one step.

  A move run that moves nothing still takes the last one's place, as [Organizing](ux.md#organizing) asks, and a run stopped while the record is written leaves the whole record of before, never half of one.

### Physical view

```
repository
├── pyproject.toml                <TOML: the package, built with setuptools, its organize-downloads command and no dependencies>
├── src/organize_downloads/
│   ├── __init__.py               <Python 3: marks the package>
│   ├── cli.py                    <Python 3: Command>
│   ├── plan.py                   <Python 3: Planner, holding the kind table of the UX>
│   ├── undo.py                   <Python 3: Undo planner>
│   ├── mover.py                  <Python 3: Mover>
│   └── record.py                 <Python 3: Record store>
└── tests/                        <Python 3, unittest: the automated tests>

the user's home
├── Downloads/                    <the folder, unless the command names another>
├── .local/state/organize-downloads/
│   └── <hash of the folder's path>.json        <JSON: the record of one folder, on Linux>
└── Library/Application Support/organize-downloads/
    └── <hash of the folder's path>.json        <JSON: the record of one folder, on macOS>
```

- The tool uses Python 3 and its standard library alone, installed by `pipx install .` as the [README](../README.md#installation) says, and is started as `organize-downloads`, which runs the Command.

- The Command takes the home from `HOME` and the folder as its full path, symbolic links resolved, and the Record store names each record by that path's hash and holds the path inside it.

  The same folder reached by two paths, such as `~/Downloads` and `/Users/me/Downloads`, then has one record.

## Test

This project has no rules of its own for how parts and user stories are checked, so what this
product's checks need is said here alone.

- Each user story and each part in `src/` is checked by automated tests in `tests/`, run from the repository with `PYTHONPATH=src python3 -m unittest discover -s tests`.
- The tests build a test folder of their own and set `HOME` to a stand-in home, so they never touch the real Downloads folder or the user's own record of a last run.
- `pyproject.toml` and the start through the installed `organize-downloads` command are left unchecked by these tests, which import the package from `src/`.

  The tests are asked only of what the tool does to a folder and to the record, and the installed command adds nothing to that but running the Command.
