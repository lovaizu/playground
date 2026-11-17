# Product vision of invoicer

## Roles

- Accounting team\
  The people who print each client's invoice with invoicer's command.
- Developer\
  The people who call invoicer's library from their own code, and install the command once for the
  accounting team.

## Objectives and key results

- O1: the accounting team bills each client what that client owes, without asking a developer.
  - KR1.1: the share of print tasks that end without the right invoice, or with a developer's
    help. Lower is better.
  - KR1.2: the time from starting a client's invoice to holding it printed, fixing invoice lines
    included. Lower is better.
- O2: the developers' own code keeps giving the results it gave before.
  - KR2.1: the share of library calls in the developers' own code that give a different result
    after they update invoicer. Lower is better.
  - KR2.2: the edits a developer makes to their own code to keep it working after they update
    invoicer. Lower is better.
- O3: a developer installs the command once, and the command runs for the accounting team from
  then on.
  - KR3.1: the share of installs that end without the command running for the accounting team.
    Lower is better.
  - KR3.2: the developer's time from starting the install to the command running for the
    accounting team. Lower is better.

KR2.1, KR1.1, KR3.1 comes first: keep a change that improves a key result only if none before it
gets worse.
Key results have no targets, as a measure made a target stops being a good measure, by Goodhart's
law. They show whether a change brought its objective closer.

## Concept

invoicer turns invoice lines into an invoice whose totals are right without anyone redoing the
math.

- Invoice lines from the spreadsheet, for O1\
  The accounting team prints from the invoice lines they keep, and the command names any bad line
  and what's wrong.
- Tax rate set at each print and never saved per client, for O1\
  The accounting team sets the tax rate anew for each invoice they print, so each client gets
  their own rate.
- Same results for developers' own code, for O2\
  The command only calls the library, which rounds tax to the cent the same way every time.
