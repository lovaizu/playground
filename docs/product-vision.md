# Product vision of invoicer

## Roles

- one from accounting\
  People in accounting who print each client's invoice from their LibreOffice Calc lines, without
  writing Python.
- one who builds invoices in Python\
  Developers who get an invoice's subtotal, tax, total, and text from its lines in Python with the
  invoicer library.

## Objectives and key results

- `O1`: one from accounting alone hands clients dated, numbered invoices bearing their names, with
  right lines, tax, and totals.
  - `KR1.1`: the share of invoices one from accounting couldn't print alone, or printed with a
    wrong line, tax, or total. Lower is better.
  - `KR1.2`: the time from the spreadsheet's lines ready to the invoice printed, reading the guide
    included. Lower is better.
- `O2`: one who builds invoices in Python gets an invoice's totals and text from their lines in
  their own code.
  - `KR2.1`: the share of invoices whose totals or text came out wrong from right lines and rate.
    Lower is better.
  - `KR2.2`: the time from lines and rate in hand to totals and text in their code, reading the
    docs included. Lower is better.

`KR1.1` and `KR2.1` come first: keep a change that improves a key result only if none before it
gets worse.
Key results have no targets, as a measure made a target stops being a good measure, by Goodhart's
law. They show whether a change brought its objective closer.

## Concept

invoicer prints the invoice straight from the accounting team's spreadsheet, given only the file,
client's name, invoice number, and rate.

- The lines as they keep them in LibreOffice Calc, for `O1`\
  They don't retype or reshape a line, so nothing is lost or mistyped on the way.
- The client's name, the invoice number, and the rate on every invoice, for `O1`\
  Each printout is a complete invoice, dated today, with no client's details taken from another.
- A stop before printing on a wrong line or rate, for `O1`\
  invoicer says which row or value to fix, so they mend it alone.
- The same sums to the cent, for `O1`\
  The printed sums match invoicer's sums for those lines and rate anywhere else, so they trust them.
- Ready in one step, for `O1`\
  The guide's one command installs invoicer, and the guide's sample invoice shows invoicer working
  before their own spreadsheet.
