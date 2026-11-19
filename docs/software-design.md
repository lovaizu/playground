# Skeleton

## Module opening

Each part is a Python module of the invoicer package, so no part holds a prompt.
Each new module opens with its one decision, in its docstring:

- [cli.py](../invoicer/cli.py), the command: the run that each command line asks for, from the values it takes to its exit status.
- [ods.py](../invoicer/ods.py), the spreadsheet reader: the lines that a Calc .ods file keeps on its first sheet under Description, Price, Quantity.
- [invoice.py](../invoicer/invoice.py), the invoice: what one invoice shows, client, number, date, and typed rate, preceding the library's sums.
- [printer.py](../invoicer/printer.py), the printer: how an invoice reaches the default printer through CUPS, and what each failure asks to check.
- [refusal.py](../invoicer/refusal.py), the refusal: what a run tells one from accounting in place of the invoice, so they mend it alone.
- The library's modules, `lines.py`, `tax.py`, `totals.py`, and `render.py`, stay as they are.

Each change names one module:

- A new column read from the sheet, or a new rule for a row, opens ods.py.
- A new line in the invoice's heading, or a new way to show the rate, opens invoice.py.
- A new failure of CUPS, or a printer named per run, opens printer.py.
- A new option, a new range for the rate, or a new sample opens cli.py.
- A new field in what a refusal tells opens refusal.py.

## Interface

```python
# invoicer/cli.py: U->>C of S1, S2, and S3
def main(argv: Sequence[str]) -> int: ...      # raises NotImplementedError("cli.main")
def run() -> None: ...                          # the console script: sys.exit(main(sys.argv[1:]))

# invoicer/ods.py: C->>R of S1 and S3
def read(path: str) -> list[Line]: ...          # raises NotImplementedError("ods.read")

# invoicer/invoice.py: C->>I of S1 and S2
@dataclass(frozen=True)
class Details:
    client: str
    number: str
    rate_typed: str                             # such as "19", for `Tax rate: 19%`
    rate: Decimal                               # such as Decimal("0.19"), for the library

@dataclass(frozen=True)
class Invoice:
    text: str

def make(lines: Sequence[Line], details: Details, today: date) -> Invoice: ...
                                                # raises NotImplementedError("invoice.make")

# invoicer/printer.py: C->>P of S1 and S2, and P->>Q to CUPS
def send(invoice: Invoice) -> None: ...         # raises NotImplementedError("printer.send")
def lp(text: str) -> subprocess.CompletedProcess[str]: ...
                                                # raises NotImplementedError("printer.lp")

# invoicer/refusal.py: R-->>C and P-->>C, as an exception
class Refusal(Exception):
    def __init__(self, fix: str, check: str = "") -> None: ...
```

- `cli.main` takes the arguments after `invoicer`, a file with `--client`, `--number`, and `--rate`, or `--sample` alone.
- `cli.main` gives 0 once the invoice shows and the printer takes it, and 1 for each refusal.
- `cli.main` writes the invoice, then `Sent to your default printer.` or the refusal, to the terminal.
- `cli.main` refuses a run with no file and no `--sample`, naming the file it needs.
- `cli.main` refuses `--sample` with a file or values, naming what to leave out.
- `cli.main` refuses an empty client or number, or a rate outside 0 to 100, before it reads the file.
- `cli.main` alone makes Details' fraction from the typed rate, holds the sample, and dates the invoice today.
- `ods.read` takes the file's path, and gives one library Line for each row that isn't blank.
- `ods.read` refuses a missing file, or a file that isn't .ods, naming the file.
- `ods.read` refuses a row 1 that lacks Description, Price, or Quantity, naming the column.
- `ods.read` refuses a row with a wrong price or quantity, or with no description, naming it as Calc does.
- `ods.read` refuses a first sheet with no line, naming the file.
- `invoice.make` takes the lines, the details, and the date that the command hands it.
- `invoice.make` gives the heading of number, client, date, and `Tax rate: 19%`, then the library's render in EUR.
- `invoice.make` hands the library only the lines and `details.rate`, and refuses nothing.
- `printer.send` takes the invoice that the command has shown, and gives nothing once lp takes the job.
- `printer.send` refuses with cups-client to install where lp is missing.
- `printer.send` refuses with `lpstat -d` to check where no default printer is set.
- `printer.send` refuses with CUPS's own reason where CUPS refuses the job.
- `printer.lp` runs lp with the text on its input and no printer named, so a test can double it.
- `Refusal` holds `fix`, what to fix or the printer's reason, and `check`, the Requirement to check or "".
- The pyproject.toml makes `run` the console script `invoicer`, with no dependency.

Each handoff fits by its types: `ods.read` gives the `list[Line]` that `invoice.make` takes.
`invoice.make` gives the `Invoice` that `printer.send` takes.
S4 reaches only the library's own calls, which stay as they are.

## Gaps

The skeleton follows each module, interface, and kind of data of the architecture, so no gap goes back to it.
