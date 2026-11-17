# Product vision of invoicer

## Roles

- Accounting team\
  The people who print each client's invoice at its tax rate with invoicer's command, from their
  spreadsheet lines.
- Developer\
  The people who call invoicer as a library from their own code, and install the command for the
  accounting team.

## Objectives and key results

- O1: the accounting team bills each client what that client owes, without asking a developer.
  - KR1.1: the share of print tasks that end without the right invoice, or with a developer's
    help. Lower is better.
  - KR1.2: the time from taking a client's invoice lines from the spreadsheet to holding the
    printed invoice. Lower is better.
- O2: the developers' own programs keep giving the invoices they gave before.
  - KR2.1: the share of the developers' existing library calls that give a different result
    after a change to invoicer. Lower is better.
  - KR2.2: the edits a developer makes to their own code to keep it working after they update
    invoicer. Lower is better.
- O3: a developer installs the command once, and after that the accounting team's invoices take
  none of the developer's time.
  - KR3.1: the share of installs after which the accounting team asks a developer for help to
    print an invoice. Lower is better.
  - KR3.2: the developer's time from starting the install to the command running for the
    accounting team. Lower is better.

KR1.1, KR2.1, KR3.1 comes first: keep a change that improves a key result only if none before it
gets worse.
Key results have no targets, as a measure made a target stops being a good measure, by Goodhart's
law. They show whether a change brought its objective closer.

## Concept

invoicer turns invoice lines into an invoice whose totals are right without anyone redoing the
math.

- Lines from the spreadsheet, for O1\
  The accounting team works from the invoice lines they already keep in their spreadsheet, so no
  one retypes a line.
- Tax rate set at each print and never saved per client, for O1\
  The accounting team sets the tax rate anew for each invoice they print, so each client gets their
  own rate.
- One rounding everywhere, for O1 and O2\
  The command and the library always round tax to the cent alike, so printed totals match what
  clients owe.
