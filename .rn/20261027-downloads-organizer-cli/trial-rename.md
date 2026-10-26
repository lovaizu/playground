# Trial: the one-step rename that refuses a taken name

For T4 in [steering.md](steering.md): does the way the Mover of
[docs/architecture.md](../../docs/architecture.md#logical-view) moves a file work, on Linux and on
macOS, before the tool is built on it? The way is one system call that renames a file and that the
system refuses when the new name is already taken, so no other program can put a file at that name
between a check and the move:

- Linux: `renameat2` with the flag `RENAME_NOREPLACE`;
- macOS: `renamex_np` with the flag `RENAME_EXCL`;

each called from Python through `ctypes`, the module of Python's standard library that calls a C
function of the system's library, as the tool is to call it.

## Check

Set before the run. Each case starts from a fresh folder holding an empty `images/` folder, and
moves `a.png` from the folder into `images/`, as a move run does. The way works on a system when
both cases pass there.

| Case | Files before | Passes when |
|---|---|---|
| free name | `a.png` holding `A` | the call returns `0`, and the folder holds only `images/a.png`, holding `A` |
| taken name | `a.png` holding `A`, `images/a.png` holding `B` | the call returns `-1` with `errno` `EEXIST` ("file exists"), and both files are still where they were, holding what they held |

## Result

| System | free name | taken name | The way works |
|---|---|---|---|
| Linux, in this environment | pass | pass | yes |
| macOS, on a GitHub Actions `macos-latest` runner | not run yet | not run yet | not known yet |

## What was run

The trial is the step `Trial of the one-step rename` of the workflow
[.github/workflows/tests.yml](../../.github/workflows/tests.yml), lines 23 to 95: a Python script
that makes its folder under the home, as the tool's Downloads folder is, runs both cases, prints
each with `PASS` or `FAIL`, removes the folder, and exits with `1` if any case failed.

### Linux

On 2026-10-26, in this environment, from the repository, the script taken out of the workflow file
and run from the home:

```sh
d=$(mktemp -d)
sed -n "/python3 - <<'EOF'/,/^ *EOF$/p" .github/workflows/tests.yml | sed '1d;$d' | sed 's/^          //' > "$d/trial.py"
(cd ~ && python3 -I "$d/trial.py"; echo "exit $?"); rm -r "$d"
```

printed:

```
python 3.14.4 | Linux-7.0.14-aarch64-with-glibc2.43
libc glibc 2.43
folder /home/agent/tmpgguhqe1a | file system: overlayfs
call renameat2(AT_FDCWD, old, AT_FDCWD, new, RENAME_NOREPLACE)
free name: returned 0, errno 0, files after {'images/a.png': 'A'} -> PASS
taken name: returned -1, errno EEXIST, files after {'a.png': 'A', 'images/a.png': 'B'} -> PASS
exit 0
```

### macOS

Not run yet: the first run on GitHub Actions stopped before the trial's step, as the last item
below tells.

## How far the result holds

- Each system was tried on one file system alone: Linux on `overlayfs`, above. A file system that
  does not offer this rename refuses the call; the architecture leaves the file in place then, and
  this trial does not show which file systems do so.
- Linux was tried with glibc 2.43 and Python 3.14.4 on aarch64 alone. `renameat2` is in glibc from
  2.28 on; with a system library that lacks it, `ctypes` cannot find the function, a case not tried.
- Only a file moved into a kind folder was tried. Moving it back, as `--undo` does, is the same
  call the other way round, not run here.
- That no other program can put a file at the name during the call rests on the call being one
  step in the system; the trial does not race another program against it.
- The first run on GitHub Actions,
  [40378426948](https://github.com/lovaizu/playground/actions/runs/40378426948), stopped on both
  runners before any step, with `The action actions/checkout@v4 is not allowed in
  lovaizu/playground because all actions must be pinned to a full-length commit SHA.`; the workflow
  now names `actions/checkout` by the commit of its tag `v4.4.0`. Nothing else failed or was worked
  around.
