# Product vision of invoicer

## Roles

- one from accounting\
  The accounting team, who print each client's invoice from their LibreOffice Calc spreadsheet's
  lines with invoicer's command, without writing Python.
- one who builds invoices in Python\
  Developers who get an invoice's subtotal, tax, total, and text from its lines in their Python code
  with invoicer's library.

## Objectives and key results

- `O1`: with no developer, one from accounting prints right invoices in clients' names, numbered,
  dated today, at their tax rates.
  - `KR1.1`: the share of invoices one from accounting couldn't print alone or printed wrong: name,
    number, date, line, tax, total. Lower is better.
  - `KR1.2`: the time from the spreadsheet's lines ready to the invoice printed, reading the
    README's guide included. Lower is better.
- `O2`: one who builds invoices in Python gets subtotal, tax, total, and text from an invoice's
  lines in their code.
  - `KR2.1`: the share of invoices whose subtotal, tax, total, or text came out wrong from right
    lines and tax rate. Lower is better.
  - `KR2.2`: the time from lines and tax rate in hand to the invoice in their code, reading the
    docs included. Lower is better.

`KR1.1` and `KR2.1` come first: keep a change that improves a key result only if none before it
gets worse.
Key results have no targets, as a measure made a target stops being a good measure, by Goodhart's
law. They show whether a change brought its objective closer.

## Concept

invoicer prints the invoice from the accounting team's spreadsheet, given the client's name,
the invoice number, and the tax rate.

- The lines as kept in the spreadsheet, for `O1`\
  The accounting team doesn't retype or reshape a line, so nothing is lost or mistyped on the way.
- The client's name, the invoice number, and the tax rate for each invoice, dated today, for `O1`\
  invoicer takes no client's details from another, so each invoice is complete.
- A stop before printing on a wrong line or tax rate, for `O1`\
  invoicer names the line or value to fix, so the accounting team mends it alone.
- The same subtotal, tax, and total to the cent, for `O1`\
  The subtotal, tax, and total match what invoicer's library gives for those lines, so the
  accounting team trusts the invoice.
- Ready in one step, for `O1`\
  The accounting team installs invoicer with the guide's one command and prints the guide's sample
  invoice before their own spreadsheet.
