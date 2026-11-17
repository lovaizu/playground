# Product vision of invoicer

## Roles

- Accounting team\
  The people who print each client's invoice with invoicer's command.
- Developer\
  The people who call invoicer as a library from their own code, and install the command once for
  the accounting team.

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

The key results rank in this order, first to last:

1. KR2.1
2. KR1.1
3. KR3.1
4. KR1.2
5. KR2.2
6. KR3.2

The developers keep a change only if no key result ranked before the one it improves gets worse.
Key results have no targets.
A measure made a target stops being a good measure, by Goodhart's law.
The key results show whether a change brought its objective closer.

## Concept

invoicer turns invoice lines into an invoice whose totals are right without anyone redoing the
math.

- Invoice lines from the spreadsheet, for O1\
  The accounting team works from the invoice lines they already keep in their spreadsheet, so
  nothing is retyped.
- Tax rate set at each print and never saved per client, for O1\
  The accounting team sets the tax rate for each invoice when they print it, so each client is
  billed at their own rate.
- One rounding everywhere, for O2\
  The tax is rounded to the cent the same way every time, both in the command and for developers
  calling the library. The developers' own code keeps the totals it got before. The printed total
  matches what's owed.
- A print that goes wrong tells the accounting team what to fix, in their words, for O1\
  When an invoice line can't be read, the command names that line and what's wrong with it. The
  accounting team fixes the line and prints again without asking a developer.
- The command adds to invoicer without changing it, for O2\
  The command only calls the library the developers already use. Updating invoicer therefore
  gives their own code the same results as before.
