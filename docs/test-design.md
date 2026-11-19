# Test cases

## End-to-end cases

[tests/test_e2e.py](../tests/test_e2e.py) holds one case for each key result, from `KR1.1` to `KR2.2`.
Each case installs the checked-out branch fresh by the README's pipx command, with the stand-in lp first on the path.
The `KR1.1` case runs the walkthrough's command at `--rate 19`, and the `KR1.2` case runs `invoicer --sample` right after the install.

## Integration cases

[tests/test_integration.py](../tests/test_integration.py) runs the joined parts through `cli.main`, one class for each story from `S1` to `S4`.
Each case builds a real .ods file, and reads what the terminal and the stand-in [tests/bin/lp](../tests/bin/lp) got.
[tests/test_contract.py](../tests/test_contract.py) checks the stand-in against CUPS's own lp, on a laptop where `INVOICER_CUPS_STATE` names its state.

## Unit cases

Each part has its file: [test_cli.py](../tests/test_cli.py), [test_ods.py](../tests/test_ods.py), [test_invoice.py](../tests/test_invoice.py), [test_printer.py](../tests/test_printer.py), and [test_refusal.py](../tests/test_refusal.py).
[test_library.py](../tests/test_library.py) holds the library's cases, which pin invoicer 1.4.0's sums and text.
The command's file holds a case for each wrong command line that `cli.main` refuses before it reads the file, naming the option:

- `test_an_option_with_no_value_after_it_is_refused`: the command line ends with `--rate` and no value.
- `test_an_option_given_twice_is_refused`: `--rate 7` follows `--rate 19`.
- `test_an_option_that_invoicer_lacks_is_refused`: `--rat 19` stands in place of `--rate 19`.

No part keeps what came before, as `P2.2` holds, so no case is a transition.
Run every case with `python3 -m unittest discover -s tests` from the repository's root.

## Trace

[tests/check_trace.py](../tests/check_trace.py) checks the trace, by the `Supports:` line of each case's docstring.
Run it with `python3 tests/check_trace.py`: it exits 0 where every key result and element has its case.

## Gaps

None: each case follows a part, interface, and kind of data that the architecture and the skeleton already draw.
