# Print a client's invoice

This guide takes you from your spreadsheet of a client's lines to that client's printed invoice.
You type no code: you save the sheet, run one command, check the invoice, and print it.

You need your Linux laptop with LibreOffice Calc and its printer set up, and the invoicer folder on
it. This guide takes the folder to be `~/invoicer`; where yours is elsewhere, use its place.

## 1. Save the client's lines

In Calc, put the client's lines on the first sheet of the file:

- The first row holds the headers `Description`, `Price`, and `Quantity`.
- Each row below it is one line of the invoice.
- A price is a number in EUR, such as `12.50`.
- A quantity is a whole number, such as `2`. Leave it empty for 1.

For example:

| Description | Price | Quantity |
|-------------|-------|----------|
| Consulting  | 120   | 3        |
| Travel      | 45.25 |          |

Save it with File > Save As, and pick ODF Spreadsheet (.ods), such as `~/invoices/acme.ods`.

## 2. Show the invoice

Open a terminal, and go to the invoicer folder:

```
cd ~/invoicer
```

Run the command with your file and the client's tax rate as a percent, such as `19` for 19 %:

```
python3 -m invoicer ~/invoices/acme.ods --tax-rate 19
```

Where the file's name holds spaces, put the name in quotes, such as `~/invoices/"acme march.ods"`.

The terminal shows the invoice, such as this one for `acme.ods` at 19 %:

```
Consulting                             360 EUR
Travel                               45.25 EUR
Subtotal                            405.25 EUR
Tax                                  77.00 EUR
Total                               482.25 EUR
```

## 3. Check the invoice

Check each line, the subtotal, the tax, and the total against your own count.

Where a line starting with `invoicer:` shows in place of the invoice, no invoice was made. The line
names the row and column of the sheet, or the tax rate, and says what to fix. Fix it in Calc and
save the file, or change the rate, then run the command again.

## 4. Print the invoice

Run the same command with `| lp` at its end, which sends the invoice to your printer:

```
python3 -m invoicer ~/invoices/acme.ods --tax-rate 19 | lp
```

The terminal shows `request id is ...`, and the printer prints the invoice.
