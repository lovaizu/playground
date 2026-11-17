# Product vision of `invoicer`

## Roles

- `accountant`\
  One on the accounting team who prints a client's invoice at that client's tax rate, with `invoicer`'s command.
- `installer`\
  A developer who sets up `invoicer`'s command on each `accountant`'s machine, installing Python and `invoicer` in place of the `accountant`.

## Objectives and key results

- `O1`: the `accountant` sends each client a correct invoice at that client's tax rate without a developer's help.
  - `KR1.1`: the share of invoices the `accountant` couldn't print without a developer's help, or printed with a wrong total. Lower is better.
  - `KR1.2`: the time from opening the spreadsheet to the printed invoice, the `accountant`'s own time included. Lower is better.
- `O2`: the `installer` gets an `accountant`'s machine ready to print invoices without anyone's further help.
  - `KR2.1`: the share of setups after which `invoicer`'s command doesn't run for the `accountant`. Lower is better.
  - `KR2.2`: the `installer`'s time from starting a setup to `invoicer`'s command running. Lower is better.

`KR1.1` and `KR2.1` comes first: keep a change that improves a key result only if none before it gets
worse.
Key results have no targets, as a measure made a target stops being a good measure, by Goodhart's
law. They show whether a change brought its objective closer.

## Concept

`invoicer` prints the finished invoice from the invoice lines as the `accountant`'s spreadsheet holds them, plus the client's tax rate.

- The spreadsheet as it is, for `O1` and `O2`\
  Neither the `accountant` nor the `installer` has a new format to learn or set up.
- Nothing wrong prints, for `O1`\
  Where `invoicer` can't read a line or the rate, it prints no invoice, only a message naming what to fix.
- The rate given each time, for `O1` and `O2`\
  Each time the `accountant` prints an invoice, they give the client's tax rate, so the `installer` sets up no rates.
