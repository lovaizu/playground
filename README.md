# `invoicer`

invoicer is a terminal command that prints an invoice from your spreadsheet's lines, named, numbered, taxed, and dated today.

invoicer is for you when you work in accounting, keep invoice lines in LibreOffice Calc, and print clients' invoices yourself. With it, you print each client a right invoice at their tax rate, with no developer's help and no Python.

## Non-goals

- invoicer doesn't make a PDF or send an email: it prints the invoice on your printer and in the terminal.
- invoicer doesn't keep a client's name or tax rate between invoices: you give both on every invoice.
- invoicer doesn't pick the next invoice number: you give the number that accounting assigns.
- invoicer doesn't print an amount in any currency but EUR.
- invoicer doesn't print addresses or VAT numbers, or your company's name: the invoice names the client only.

## Requirements

- An `.ods` file with lines under Description, Price, and Quantity on its first sheet: row 1 in Calc shows them.
- Python 3.9 or later: `python3 --version` shows it.
- pipx, from `sudo apt install pipx` on Debian or Ubuntu, or `sudo dnf install pipx` on Fedora, then `pipx ensurepath` and a new terminal: `pipx --version` shows it.
- A default printer, and `lpstat` from `sudo apt install cups-client` or `sudo dnf install cups-client` where it's missing: `lpstat -d` shows `system default destination:` and its name.

## Installation

```console
pipx install https://github.com/lovaizu/playground/archive/refs/heads/main.zip
```

`invoicer --sample` prints invoicer 1.4.0's sample invoice of 119.00 EUR on your printer and screen.

## Walkthrough

At the end, you have Nordwind GmbH's invoice 2026-031 on paper, at their tax rate of 19%.

Your spreadsheet `October.ods` keeps the invoice's lines on its first sheet:

| Description          | Price  | Quantity |
| -------------------- | ------ | -------- |
| Bookkeeping, October | 85.00  | 12       |
| Payroll, October     | 14.50  | 9        |
| Annual accounts 2025 | 450.00 | 1        |

In the terminal, in the spreadsheet's folder, you run one command:

```console
$ invoicer October.ods --client "Nordwind GmbH" --number 2026-031 --rate 19
Invoice 2026-031
Client: Nordwind GmbH
Date: 2026-11-19
Tax rate: 19%

Bookkeeping, October               1020.00 EUR
Payroll, October                    130.50 EUR
Annual accounts 2025                450.00 EUR
Subtotal                           1600.50 EUR
Tax                                 304.10 EUR
Total                              1904.60 EUR

Sent to your default printer.
```

The same invoice comes out of your printer. invoicer rounds the tax of 304.095 EUR to 304.10 EUR, to the cent.

## How it works

invoicer prints the invoice straight from your own spreadsheet, given only the file, client's name, invoice number, and rate.

![How invoicer works](images/how-it-works.svg)

### Today, an invoice needs a developer who writes Python

As invoicer needs only the file and three values you already know, one command prints the invoice. You need no code.

### Does it read your spreadsheet as you keep it?

invoicer reads your own file, the lines on its first sheet under Description, Price, and Quantity, and skips other columns. You don't retype a line.

### Is the tax right for this client?

You give the client's rate on every invoice, so invoicer never takes one from another client. Its subtotal, tax, and total come out the same to the cent each time, as the walkthrough's sums show.

### What if a line or the rate is wrong?

As invoicer reads your own file, it names the row or value to fix before printing, such as `row 3: the price "14,50 EUR" isn't a number`. Nothing prints: you fix that cell in your own spreadsheet, and run the command again.

### Can you set it up yourself?

As invoicer needs only your file and three values, nothing waits to set up after one install command. Its sample invoice shows it print before you give it your own spreadsheet.

## Documentation

- [Issues](https://github.com/lovaizu/playground/issues): for anyone who needs help or finds a wrong invoice.
- [Product vision](docs/product-vision.md): for developers who build on invoicer, what it's for and why.

## License

[No license is granted yet](https://choosealicense.com/no-permission/)
