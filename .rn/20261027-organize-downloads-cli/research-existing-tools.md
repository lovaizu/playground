# Research: an existing tool, or one made here

Checked on 2026-10-27.

## Question

For T1 action 2, where the user settles whether `sort-downloads` is an existing tool used as it is
or one made here, and in what language and way of installing:

1. Does an existing tool already sort the files directly in a folder into folders by kind, with a
   preview, and an undo of the last sort, on both Linux and macOS? How near does each come to AC1
   to AC3 and AC8, and do its licence and price allow using it here?
2. For a tool made here, which ways of building and installing it run alike on Linux and macOS
   with what a Mac already has?

## Answer

No existing tool found meets AC1 to AC3 and AC8, so the choice favoured is to make the tool here.
The nearest are organize, which has a preview but no undo, and TidyMate, which has both but renames
a file whose name is taken instead of leaving it (G1 and AC3 forbid that) and does not list, before
undoing, each file it would move back (AC8 asks for that). Using either one would mean changing its
code, which is making the tool anyway.

For a tool made here, the favoured way is one Python 3 file using only the standard library,
installed by copying it from the clone into a folder on the user's `PATH`. It needs no build step
and no package manager, and it runs on Linux and on a Mac that has `python3`. Whether the user's Mac
has `python3`, and which version, is the one point the README and the architecture must not guess
(see "Not settled"). The other ways and their costs are in the second table.

## Existing tools against AC1 to AC3 and AC8

| Tool | Runs on | Preview (AC1) | Name already taken (AC3) | Undo of the last sort (AC8) | Licence, price | Other gaps |
|---|---|---|---|---|---|---|
| [organize](https://github.com/tfeldmann/organize) 3.3.0, 2024-11-25 ([PyPI](https://pypi.org/project/organize-tool/)) | macOS, Windows, Linux ([README](https://github.com/tfeldmann/organize#readme)); Python 3.9 or newer, below 4.0 ([PyPI](https://pypi.org/pypi/organize-tool/json) `requires_python`) | `organize sim` shows what would happen and touches nothing ([README](https://github.com/tfeldmann/organize#readme)) | the `move` action takes `on_conflict: skip` ([actions](https://organize.readthedocs.io/en/latest/actions/)); the default is `rename_new` | none: the request, [issue #16](https://github.com/tfeldmann/organize/issues/16), has been open since 2018-10-03 | MIT, free | the kinds and the target folders have to be written by the user in a YAML config file; by default it does not look into subfolders (`subfolders`, default `false`, [rules](https://organize.readthedocs.io/en/latest/rules/)) |
| [TidyMate](https://github.com/Anand2k29/TidyMate) 1.0.0, 2026-10-10 ([PyPI](https://pypi.org/project/tidymate/)) | Windows, macOS, Linux, Python 3.8 or newer ([README](https://github.com/Anand2k29/TidyMate#readme)) | `tidymate tidy <folder> --dry-run` ([README](https://github.com/Anand2k29/TidyMate#readme)) | renamed to `name (1).ext` ([`build_plan`](https://github.com/Anand2k29/TidyMate/blob/ecf1080f69c18830bc76970c479f1cb591279afe/tidymate/smart_organizer.py#L139-L145)) | `--undo` prints only how many files, asks yes or no, has no dry run; a file whose old place is taken is put back under a new name ([`run_undo`](https://github.com/Anand2k29/TidyMate/blob/ecf1080f69c18830bc76970c479f1cb591279afe/tidymate/smart_organizer.py#L197-L211), [`undo_log`](https://github.com/Anand2k29/TidyMate/blob/ecf1080f69c18830bc76970c479f1cb591279afe/tidymate/common.py#L138-L166)); it removes only the folders it made, and only when empty | MIT, free | a file with no extension, or one changed in the last 5 minutes, is skipped, not put in Other (AC2); run with no folder named, it prints its help instead of using ~/Downloads (AC4); first released 2026-10-10, 5 stars |
| [downloads-folder-organizer](https://github.com/ajitfawade/downloads-folder-organizer), last change 2025-09-12 | macOS and Linux, a bash script | none: running it moves the files at once ([script](https://github.com/ajitfawade/downloads-folder-organizer/blob/c3a796b52ae1b1dd1ec39b28f42edca37eefadfd/organize_downloads.sh)) | renamed to `name_1.ext` ([lines 160-174](https://github.com/ajitfawade/downloads-folder-organizer/blob/c3a796b52ae1b1dd1ec39b28f42edca37eefadfd/organize_downloads.sh#L160-L174)) | writes an undo script into Downloads; it runs `mv` back without checking the old place, so a new file of the same name there is overwritten ([lines 340-350](https://github.com/ajitfawade/downloads-folder-organizer/blob/c3a796b52ae1b1dd1ec39b28f42edca37eefadfd/organize_downloads.sh#L340-L350)) | MIT, free | always works on ~/Downloads |
| [Hazel](https://www.noodlesoft.com/) 6 | macOS only | not checked | not checked | not checked | paid, $42 ([store](https://www.noodlesoft.com/store/)) | no Linux, so it fails G1 whatever it does |

MIT lets anyone use, change and share the code, provided the copyright and licence notice are kept
([licence text](https://opensource.org/license/mit)). So the licences would not stop us using any
of the three free tools; their behaviour does.

## Ways of making the tool here, on Linux and macOS

| Way | What a Mac has for it | Install from a fresh clone | Cost |
|---|---|---|---|
| One Python 3 file, standard library only (favoured) | macOS has had no Python 2 since 12.3, and Apple tells developers to use Python 3 ([macOS 12.3 release notes](https://developer.apple.com/documentation/macos-release-notes/macos-12_3-release-notes)). In 10.15 Apple said future versions of macOS will not include scripting language runtimes such as Python by default, and might need extra packages installed ([macOS 10.15 release notes](https://developer.apple.com/documentation/macos-release-notes/macos-catalina-10_15-release-notes)). | copy or link the file into a folder on `PATH`, such as `~/.local/bin`; no build | only works where `python3` is there; the lowest Python version it supports must be one the user's Mac has |
| The same file installed with `pip` or `pipx` | as above, plus `pip` | `pipx install .` or `pip install .` | adds a packaging file; where Python is marked "externally managed" ([PEP 668](https://peps.python.org/pep-0668/)), as on many Linux distributions, `pip install` outside a virtual environment is refused, so the README would need a step for that |
| A bash script | `/bin/bash` on macOS is bash 3.2 (Apple's source is [bash-3.2](https://github.com/apple-oss-distributions/bash)); zsh has been the default login shell since macOS 10.15, but bash is still there ([Apple](https://support.apple.com/en-us/102360)) | copy the script into a folder on `PATH` | nothing to install, but it has to keep to bash 3.2 and to options that macOS's BSD tools and Linux's GNU tools share; keeping the record of the last sort exact for any file name, spaces and new lines included, is harder in shell than in Python (our judgement, not a sourced fact) |
| A compiled program, such as Go or Rust | nothing: the compiler is not part of macOS | install the compiler, then build; or download a built program from a release | AC7 asks that a reader install from a fresh clone, which here means installing a compiler first |

## Not settled

- Whether the user's Mac has `python3`, and which version. Apple's notes above say Python might need
  an extra package; they do not say which version that package gives. Settled by the user running
  `python3 --version` on their Mac. If it is missing, the user decides between installing it and
  choosing the bash way instead.
- Whether the kinds and file extensions the tool uses suit the user's ~/Downloads. AC6 settles
  this, once there is a tool to try.
