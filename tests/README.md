# Test cases

Run every case from the repository's top with `python3 -m unittest`. The tests use only Python's
standard library: they build each .ods sheet they read, and put a stand-in `lp` on PATH that
records the page it gets.

## End-to-end cases

[test_e2e.py](test_e2e.py) runs `invoicer print` as the guide's Walkthrough does, on the guide's
Nordwind sheet and on a month's sheet of 60 lines that runs past one printed page, for KR1.1 and
KR1.2, and the library's calls as a developer makes them, for KR2.1. It runs the checked-out code
by `python3 -m invoicer`, never an `invoicer` on PATH, so an installed copy changes no result.

## Integration cases

[test_integration.py](test_integration.py) runs the command with the Rate reader, the Sheet
reader, the Invoice page, and the Printer joined, a case for each path of S1 to S4, each principle
item, each component's own decision, and each handoff.

## Unit cases

[test_sheet.py](test_sheet.py), [test_rate.py](test_rate.py), [test_page.py](test_page.py), and
[test_printer.py](test_printer.py) hold a case for each class of what the module's interface takes
or gives. [test_library.py](test_library.py) holds the library regression: it passes before
anything new is built, and fails where a change breaks a developer's call. The integration case
that invoicer needs only Python's standard library is a guard in the same way: it passes before
the build, and fails once a package is added.

## Trace

`python3 tests/trace.py` gives 0 where every key result has an E2E case, every element of the
architecture an integration case, and every name that a case's `Supports:` line gives exists.

## Gaps

None.
