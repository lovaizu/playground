# Product vision of `invoicer`

## Roles

- `accountant`\
  One on the accounting team who prints a client's invoice at that client's tax rate, with `invoicer`'s command.
- `installer`\
  A developer who sets up `invoicer`'s command on each `accountant`'s machine, so the `accountant` installs nothing.

## Objectives and key results

- `O1`: the `accountant` sends each client a correct invoice at that client's tax rate without anyone's help.
  - `KR1.1`: where `invoicer`'s command runs, the share of invoices that needed someone's help or had a wrong total. Lower is better.
  - `KR1.2`: the time from opening the spreadsheet to the printed invoice, the `accountant`'s own time included. Lower is better.
- `O2`: the `installer` gets an `accountant`'s machine ready to print invoices without anyone's further help.
  - `KR2.1`: the share of setups after which `invoicer`'s command doesn't run for the `accountant`. Lower is better.
  - `KR2.2`: the `installer`'s time from starting a setup to `invoicer`'s command running. Lower is better.

`KR1.1` and `KR2.1` comes first: keep a change that improves a key result only if none before it gets
worse.
Key results have no targets, as a measure made a target stops being a good measure, by Goodhart's
law. They show whether a change brought its objective closer.

## Concept

`invoicer`'s command prints the finished invoice from the invoice lines in the `accountant`'s spreadsheet, plus the client's tax rate.

- The spreadsheet as it is, for `O1`\
  The `accountant` learns no new format, since `invoicer`'s command takes the lines as they already keep them.
- Nothing wrong prints, for `O1`\
  For an unreadable line or rate, `invoicer`'s command prints only a message naming the line or value to fix.
- The rate given each time, for `O1`\
  Each time the `accountant` prints an invoice, they give the client's tax rate, as `invoicer`'s command remembers none.
