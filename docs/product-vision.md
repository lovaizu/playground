# Product vision of invoicer

## Roles

invoicer serves two kinds of people, each with a goal of their own.

- Accounting team\
  The people who run invoicer's command to print each client's invoice, at that client's tax
  rate, from the invoice lines they keep in a spreadsheet, without touching Python tooling.
- Developer\
  The people who call invoicer as a library from their own code, and who install the command once
  for the accounting team.

## Objectives and key results

Each objective is the end that one role reaches with invoicer, and its two key results measure
how well and how fast the role reaches it.

- O1: the accounting team bills each client what that client owes, without asking a developer.
  - KR1.1: the share of the accounting team's print tasks that end with no invoice, with an
    invoice whose total differs from what the client owes, or with a developer asked for help.
    Lower is better.
  - KR1.2: the time from the accounting team taking a client's invoice lines from the spreadsheet
    to their holding the printed invoice. Lower is better.
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

`KR<n>.1` comes first: keep a change that improves a key result only if none before it gets
worse.
Key results have no targets, as a measure made a target stops being a good measure, by Goodhart's
law. The key results show whether a change brought its objective closer.

## Concept

invoicer turns invoice lines into an invoice whose totals are right without anyone redoing the
math.
Each choice in invoicer leans toward this way, and the three ideas below keep it holding.

- Lines from the spreadsheet, for O1\
  The accounting team works from the invoice lines they already keep in their spreadsheet, so no
  one retypes a line.
- Tax rate set at each print, for O1\
  The accounting team sets the tax rate for each invoice when they print it, and invoicer doesn't
  save it per client, so each client gets an invoice at their own rate.
- One rounding everywhere, for O1 and O2\
  The command and the library that developers call round the tax to the cent the same way every
  time, so the printed total matches what the client owes.
