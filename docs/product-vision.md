# Product vision of `invoicer`

`invoicer` gives the `accountant` a command that prints a client's invoice from the invoice lines
that the `accountant` keeps in a spreadsheet, at that client's tax rate.

## Roles

`invoicer` serves two roles, each with a job of its own.

- `accountant`\
  One on the accounting team who prints a client's invoice at that client's tax rate.
- `installer`\
  A developer who sets up `invoicer`'s command on each `accountant`'s machine, installing Python and `invoicer` in place of the `accountant`.

## Objectives and key results

Each objective, marked `O`, states what one role is trying to achieve.
Its key results, marked `KR`, are measures that show whether a change brought the objective closer.

- `O1`: the `accountant` sends each client a correct invoice at that client's tax rate without a developer's help.
  - `KR1.1`: the share of invoices the `accountant` couldn't print without help or that came out with a wrong total. Lower is better.
  - `KR1.2`: the time from opening the spreadsheet to the printed invoice, the `accountant`'s own time included. Lower is better.
- `O2`: the `installer` gets an `accountant`'s machine ready to print invoices without anyone's further help.
  - `KR2.1`: the share of setups after which `invoicer`'s command doesn't run for the `accountant`. Lower is better.
  - `KR2.2`: the `installer`'s time from starting a setup to `invoicer`'s command running. Lower is better.

`KR1.1` ranks before `KR1.2`, and `KR2.1` ranks before `KR2.2`.
Keep a change that improves a key result only if no key result ranked before it gets worse.
Key results have no targets.
People who aim at a number improve the number in place of what the `accountant` or the `installer` achieves.

## Concept

The `accountant` gives `invoicer`'s command the invoice lines as the `accountant`'s spreadsheet already holds them, plus the client's tax rate, and `invoicer` prints the finished invoice.

- The spreadsheet as it is, for `O1` and `O2`\
  The `accountant` learns no new format.
  The `installer` sets up no format on the `accountant`'s machine.
- Nothing wrong prints, for `O1`\
  Where `invoicer` can't read a line or the rate, `invoicer` prints nothing.
  `invoicer`'s message says which line or value to fix.
  The `accountant` fixes that line or value and runs `invoicer`'s command again.
- The rate given each time, for `O1` and `O2`\
  Each time the `accountant` prints an invoice, they give the client's tax rate.
  `invoicer` remembers no rate for any client.
  The `installer` sets up no rates on the `accountant`'s machine.
