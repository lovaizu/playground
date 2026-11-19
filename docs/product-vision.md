# Product vision of invoicer

## Roles

- one from accounting\
  People in accounting who print a client's invoice at its rate from their Calc lines, with
  invoicer's command and guide.
- one who builds invoices in Python\
  Developers who get an invoice's subtotal, tax, total, and text from its lines in Python with the
  invoicer library.

## Objectives and key results

- `O1`: one from accounting hands each client an invoice with right lines, tax at that client's
  rate, and total, unaided.
  - `KR1.1`: the share of invoices one from accounting couldn't print alone, or printed with a
    wrong line, tax, or total. Lower is better.
  - `KR1.2`: the time from the spreadsheet's lines ready to the invoice printed, reading the guide
    included. Lower is better.
- `O2`: one who builds invoices in Python gets an invoice's totals and text from their lines in
  their own code.
  - `KR2.1`: the share of invoices whose totals or text came out wrong from right lines and rate.
    Lower is better.
  - `KR2.2`: the time from lines and rate in hand to totals and text in their code, docs reading
    included. Lower is better.

`KR1.1` and `KR2.1` comes first: keep a change that improves a key result only if none before it
gets worse.
Key results have no targets, as a measure made a target stops being a good measure, by Goodhart's
law. They show whether a change brought its objective closer.

## Concept

invoicer prints the invoice straight from the accounting team's own spreadsheet, given only the file
and the client's rate.

- The lines as they keep them in Calc, for `O1`\
  They don't retype or reshape a line, so nothing is lost or mistyped on the way.
- The rate on every invoice, for `O1`\
  No client's rate is assumed for another.
- A stop before printing on a wrong line or rate, for `O1`\
  It says which row or value to fix, so they mend it alone.
- The same sums as the library, for `O1`\
  The totals it prints are the ones the developers already get from invoicer and trust.
