# Product vision of `invoicer`

## Roles

- `accountant`\
  One on the accounting team who prints a client's invoice from their spreadsheet, at that client's tax rate.
- `installer`\
  A developer who installs Python and invoicer on the accounting team's machines, so the team installs nothing.

## Objectives and key results

- `O1`: the accountant sends each client a correct invoice at that client's tax rate without a developer's help.
  - `KR1.1`: the share of invoices the accountant couldn't print without help or that came out with a wrong total. Lower is better.
  - `KR1.2`: the time from opening the spreadsheet to the printed invoice, the accountant's own time included. Lower is better.
- `O2`: the installer gets an accountant's machine ready to print invoices without anyone's further help.
  - `KR2.1`: the share of setups after which the command doesn't run for the accountant. Lower is better.
  - `KR2.2`: the installer's time from starting a setup to the command running. Lower is better.

`KR1.1` and `KR2.1` comes first: keep a change that improves a key result only if none before it gets
worse.
Key results have no targets, as a measure made a target stops being a good measure, by Goodhart's
law. They show whether a change brought its objective closer.

## Concept

`invoicer` takes the invoice lines as the accountant keeps them, plus the client's tax rate, and returns the finished invoice.

- Their spreadsheet as it is, for `O1` and `O2`\
  The accountant learns no new format, and the installer configures none.
- Nothing wrong prints, for `O1`\
  An unreadable line or rate stops the print, and the command names what to fix.
- Rate given each time, for `O1` and `O2`\
  The accountant gives each invoice its rate, and the installer configures none.
