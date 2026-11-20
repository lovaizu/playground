"""The unit cases of main, the command."""

from __future__ import annotations

import io
import random
from decimal import ROUND_HALF_UP, Decimal

from invoicer.__main__ import main
from tests._ods import HEADER, Folder

USAGE = "invoicer: usage: python3 -m invoicer <spreadsheet.ods> --tax-rate <percent>, such as invoice.ods --tax-rate 19\n"


def invoice_row(label, amount):
    """One row of the invoice's text, as render lays it out."""
    return f"{label:<30}{amount:>12} EUR"


def invoice_of_hundred(tax, total):
    """The text that main writes for the invoice of one line, Design at 100, with that tax and total."""
    rows = [("Design", "100"), ("Subtotal", "100"), ("Tax", tax), ("Total", total)]
    return "".join(invoice_row(label, amount) + "\n" for label, amount in rows)


def rate_refused(given):
    return f'invoicer: --tax-rate must be a percent from 0 to 100, such as 19, 7.5, or 19%, not "{given}"\n'


def fraction_refused(given, percent):
    return (
        f'invoicer: --tax-rate is a percent, so "{given}" would be {given} %;'
        f" write {percent} for {percent} %\n"
    )


class Main(Folder):
    def run_main(self, argv):
        """Runs main on argv, and gives its status, what it wrote to stdout, and to stderr."""
        stdout, stderr = io.StringIO(), io.StringIO()
        status = main(argv, stdout, stderr)
        return status, stdout.getvalue(), stderr.getvalue()

    def hundred(self):
        """A sheet of one line of 100."""
        return self.sheet([HEADER, ["Design", 100, 1]])

    def test_main_takes_19_as_19_percent(self):
        """Given a sheet of one line of 100,
        when main runs with --tax-rate 19,
        then it writes the invoice with a tax of 19.00 and a total of 119.00, and gives 0.

        Traces: U-main, S1, command.
        """
        result = self.run_main([self.hundred(), "--tax-rate", "19"])

        self.assertEqual(result, (0, invoice_of_hundred("19.00", "119.00"), ""))

    def test_main_takes_7_5_as_7_5_percent(self):
        """Given a sheet of one line of 100,
        when main runs with --tax-rate 7.5,
        then it writes the invoice with a tax of 7.50 and a total of 107.50, and gives 0.

        Traces: U-main, S1, command.
        """
        result = self.run_main([self.hundred(), "--tax-rate", "7.5"])

        self.assertEqual(result, (0, invoice_of_hundred("7.50", "107.50"), ""))

    def test_main_takes_19_with_a_percent_sign_as_19_percent(self):
        """Given a sheet of one line of 100,
        when main runs with --tax-rate 19%,
        then it writes the invoice with a tax of 19.00 and a total of 119.00, and gives 0.

        Traces: U-main, S1, command.
        """
        result = self.run_main([self.hundred(), "--tax-rate", "19%"])

        self.assertEqual(result, (0, invoice_of_hundred("19.00", "119.00"), ""))

    def test_main_accepts_a_rate_of_0(self):
        """Given a sheet of one line of 100,
        when main runs with --tax-rate 0,
        then it writes the invoice with a tax of 0.00, and gives 0.

        Traces: U-main, S1, command.
        """
        result = self.run_main([self.hundred(), "--tax-rate", "0"])

        self.assertEqual(result, (0, invoice_of_hundred("0.00", "100.00"), ""))

    def test_main_accepts_a_rate_of_100(self):
        """Given a sheet of one line of 100,
        when main runs with --tax-rate 100,
        then it writes the invoice with a tax of 100.00, and gives 0.

        Traces: U-main, S1, command.
        """
        result = self.run_main([self.hundred(), "--tax-rate", "100"])

        self.assertEqual(result, (0, invoice_of_hundred("100.00", "200.00"), ""))

    def test_main_accepts_a_rate_of_1(self):
        """Given a sheet of one line of 100,
        when main runs with --tax-rate 1, the least rate over 0 that it takes,
        then it writes the invoice with a tax of 1.00, and gives 0.

        Traces: U-main, S1, command.
        """
        result = self.run_main([self.hundred(), "--tax-rate", "1"])

        self.assertEqual(result, (0, invoice_of_hundred("1.00", "101.00"), ""))

    def test_main_refuses_a_rate_of_0_19_written_as_a_fraction(self):
        """Given a sheet of one line,
        when main runs with --tax-rate 0.19, as if for 19 %,
        then it writes one line telling to write 19 for 19 % to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, P2, command.
        """
        self.assertEqual(self.run_main([self.hundred(), "--tax-rate", "0.19"]), (2, "", fraction_refused("0.19", "19")))

    def test_main_refuses_a_rate_of_0_19_with_a_percent_sign(self):
        """Given a sheet of one line,
        when main runs with --tax-rate 0.19%,
        then it writes one line telling to write 19 for 19 % to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, P2, command.
        """
        self.assertEqual(
            self.run_main([self.hundred(), "--tax-rate", "0.19%"]),
            (2, "", 'invoicer: --tax-rate is a percent, so "0.19%" would be 0.19 %; write 19 for 19 %\n'),
        )

    def test_main_refuses_a_rate_of_0_99_just_below_1(self):
        """Given a sheet of one line,
        when main runs with --tax-rate 0.99,
        then it writes one line telling to write 99 for 99 % to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, P2, command.
        """
        self.assertEqual(self.run_main([self.hundred(), "--tax-rate", "0.99"]), (2, "", fraction_refused("0.99", "99")))

    def test_main_refuses_a_rate_of_0_075_with_the_percent_it_stands_for(self):
        """Given a sheet of one line,
        when main runs with --tax-rate 0.075, as if for 7.5 %,
        then it writes one line telling to write 7.5 for 7.5 % to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, P2, command.
        """
        self.assertEqual(self.run_main([self.hundred(), "--tax-rate", "0.075"]), (2, "", fraction_refused("0.075", "7.5")))

    def test_main_refuses_a_rate_of_minus_1(self):
        """Given a sheet of one line,
        when main runs with --tax-rate -1,
        then it writes one line naming --tax-rate to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, P2, command.
        """
        self.assertEqual(self.run_main([self.hundred(), "--tax-rate", "-1"]), (2, "", rate_refused("-1")))

    def test_main_refuses_a_rate_of_101(self):
        """Given a sheet of one line,
        when main runs with --tax-rate 101,
        then it writes one line naming --tax-rate to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, P2, command.
        """
        self.assertEqual(self.run_main([self.hundred(), "--tax-rate", "101"]), (2, "", rate_refused("101")))

    def test_main_refuses_a_rate_that_isnt_a_number(self):
        """Given a sheet of one line,
        when main runs with --tax-rate abc,
        then it writes one line naming --tax-rate to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, P2, command.
        """
        self.assertEqual(self.run_main([self.hundred(), "--tax-rate", "abc"]), (2, "", rate_refused("abc")))

    def test_main_refuses_a_rate_of_nan(self):
        """Given a sheet of one line,
        when main runs with --tax-rate NaN, which Python reads as a number,
        then it writes one line naming --tax-rate to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, P2, command.
        """
        self.assertEqual(self.run_main([self.hundred(), "--tax-rate", "NaN"]), (2, "", rate_refused("NaN")))

    def test_main_checks_the_rate_before_the_sheet(self):
        """Given a path where no file lies,
        when main runs on it with --tax-rate abc,
        then the one line on stderr names --tax-rate, as the rate is checked first.

        Traces: U-main, S2, P2, command.
        """
        missing = self.path("missing.ods")

        self.assertEqual(self.run_main([missing, "--tax-rate", "abc"]), (2, "", rate_refused("abc")))

    def test_main_refuses_a_missing_path_with_the_usage(self):
        """Given no spreadsheet path,
        when main runs with --tax-rate 19 alone,
        then it writes the usage to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, command.
        """
        self.assertEqual(self.run_main(["--tax-rate", "19"]), (2, "", USAGE))

    def test_main_refuses_a_missing_tax_rate_with_the_usage(self):
        """Given a sheet of one line,
        when main runs with its path alone,
        then it writes the usage to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, command.
        """
        self.assertEqual(self.run_main([self.hundred()]), (2, "", USAGE))

    def test_main_writes_a_sheet_error_as_one_line_with_status_2(self):
        """Given a sheet whose row 2 has a text price,
        when main runs on it with --tax-rate 19,
        then it writes the sheet reader's refusal as one line to stderr, nothing to stdout, and gives 2.

        Traces: U-main, S2, P2, command.
        """
        path = self.sheet([HEADER, ["Design", "lots", 1]])

        self.assertEqual(
            self.run_main([path, "--tax-rate", "19"]),
            (
                2,
                "",
                f'invoicer: {path}: first sheet "Sheet1", row 2, column B (Price) holds "lots", not a number;'
                " enter the price as a number, such as 12.50\n",
            ),
        )


class Totals(Folder):
    def test_property_total_is_subtotal_plus_its_tax_and_subtotal_is_the_exact_sum_of_the_cells(self):
        """Given sheets of 1 to 8 lines of random prices to the tenth of a cent and quantities, made
        from fixed seeds,
        when main runs on each with a random rate of 0, or of 1 to 100 to the tenth,
        then the invoice's subtotal is the exact sum of price, rounded half up to the cent, times
        quantity of the cells, and its total is that subtotal plus its tax at the rate, rounded half
        up to the cent.

        Traces: Property, S1, command, render.
        """
        for seed in range(40):
            with self.subTest(seed=seed):
                pick = random.Random(seed)
                cells = [
                    (Decimal(pick.randint(-50000, 500000)) / 1000, pick.randint(1, 20))
                    for _ in range(pick.randint(1, 8))
                ]
                percent = Decimal(pick.choice([0, *range(10, 1001)])) / 10
                path = self.sheet([HEADER] + [[f"Item {n}", price, quantity] for n, (price, quantity) in enumerate(cells)])
                stdout = io.StringIO()

                main([path, "--tax-rate", str(percent)], stdout, io.StringIO())

                shown = {line[:30].strip(): Decimal(line[30:].split()[0]) for line in stdout.getvalue().splitlines()}
                cent = Decimal("0.01")
                exact = sum((price.quantize(cent, ROUND_HALF_UP) * quantity for price, quantity in cells), Decimal(0))
                tax = (exact * percent / 100).quantize(cent, rounding=ROUND_HALF_UP)
                self.assertEqual(shown["Subtotal"], exact, "the subtotal is the exact sum of the cells")
                self.assertEqual(shown["Total"], exact + tax, "the total is the subtotal plus its tax")
