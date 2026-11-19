"""The unit cases of the command, cli.main and cli.run.

The command reaches each part through its module, as `ods.read`, `invoice.make`, and
`printer.send`, so each case puts a double in each part's place. Each docstring names, after
Supports, the integration case of tests/test_integration.py that it supports.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import sys
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

from spreadsheet import SENT, WALKTHROUGH_ARGS

from invoicer import Line, cli, invoice, ods, printer
from invoicer.invoice import Details, Invoice
from invoicer.refusal import Refusal

LINES = [Line("Bookkeeping, October", Decimal("85.00"), 12)]
TEXT = "Invoice 2026-031\n(the rest of the invoice)"
MAKE = inspect.signature(invoice.make)


def argv_with(**given: str) -> list[str]:
    """The walkthrough's command line, with each option given in place of its own."""
    argv = list(WALKTHROUGH_ARGS)
    for name, value in given.items():
        argv[argv.index(f"--{name}") + 1] = value
    return argv


def argv_without(name: str) -> list[str]:
    """The walkthrough's command line without the option `name` and its value."""
    argv = list(WALKTHROUGH_ARGS)
    at = argv.index(f"--{name}")
    return argv[:at] + argv[at + 2 :]


class MainTest(unittest.TestCase):
    """cli.main, with a double in place of the reader, the invoice, and the printer."""

    read: mock.MagicMock
    make: mock.MagicMock
    send: mock.MagicMock

    def setUp(self) -> None:
        """Puts the doubles in place: the reader gives LINES, make gives TEXT, and send takes it."""
        for module, name, kept in (
            (ods, "read", LINES),
            (invoice, "make", Invoice(TEXT)),
            (printer, "send", None),
        ):
            double = mock.patch.object(module, name, autospec=True, return_value=kept)
            setattr(self, name, double.start())
            self.addCleanup(double.stop)

    def main(self, argv: list[str]) -> tuple[int, str, str]:
        """The exit status, terminal output, and error output of cli.main on `argv`."""
        self.out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, self.out.getvalue(), err.getvalue()

    def made(self) -> tuple[list[Line], Details, date]:
        """The lines, details, and date of the last call of make, however the command passed them."""
        call = self.make.call_args
        held = MAKE.bind(*call[0], **call[1]).arguments
        return held["lines"], held["details"], held["today"]

    def assert_refused(self, argv: list[str], *names: str) -> None:
        """cli.main on `argv` ends with 1, names each of `names`, and reaches no part."""
        code, out, err = self.main(argv)
        self.assertEqual(code, 1, out + err)
        for name in names:
            self.assertIn(name, out + err)
        self.read.assert_not_called()
        self.make.assert_not_called()
        self.send.assert_not_called()

    def test_a_file_with_every_value_is_shown_printed_and_gives_0(self) -> None:
        """Supports: test_s1_prints_the_walkthrough_invoice.

        Given the walkthrough's command line.
        When cli.main runs it.
        Then it reads October.ods, has the invoice made of its lines and details dated today,
        shows it, then that it went to the default printer, has it printed, and gives 0.
        """
        code, out, _ = self.main(list(WALKTHROUGH_ARGS))
        self.read.assert_called_once_with("October.ods")
        details = Details("Nordwind GmbH", "2026-031", "19", Decimal("0.19"))
        self.make.assert_called_once_with(LINES, details, date.today())
        self.send.assert_called_once_with(Invoice(TEXT))
        self.assertEqual(out.splitlines(), TEXT.splitlines() + ["", SENT])
        self.assertEqual(code, 0)

    def test_the_rate_is_handed_as_typed_and_as_a_fraction(self) -> None:
        """Supports: test_s1_taxes_at_the_typed_rate.

        Given --rate 19, 7, 0, 100, or 19.5, from 0 to 100 and its ends included.
        When cli.main runs it.
        Then the details hold the rate as typed, and its fraction, such as 0.19 for 19.
        """
        for typed, fraction in (
            ("19", "0.19"),
            ("7", "0.07"),
            ("0", "0"),
            ("100", "1"),
            ("19.5", "0.195"),
        ):
            with self.subTest(rate=typed):
                self.make.reset_mock()
                self.assertEqual(self.main(argv_with(rate=typed))[0], 0)
                details = self.made()[1]
                self.assertEqual(details.rate_typed, typed)
                self.assertEqual(details.rate, Decimal(fraction))

    def test_a_rate_that_isnt_a_number_from_0_to_100_is_refused(self) -> None:
        """Supports: test_s3_names_a_rate_beyond_100.

        Given --rate -0.01 or 100.01 just past either end, 119, abc, or "".
        When cli.main runs it.
        Then it names --rate, reads no file, and gives 1.
        """
        for typed in ("-0.01", "100.01", "119", "abc", ""):
            with self.subTest(rate=typed):
                self.assert_refused(argv_with(rate=typed), "--rate")

    def test_a_missing_rate_is_refused(self) -> None:
        """Supports: test_s3_names_a_rate_beyond_100.

        Given the walkthrough's command line without --rate.
        When cli.main runs it.
        Then it names --rate, reads no file, and gives 1.
        """
        self.assert_refused(argv_without("rate"), "--rate")

    def test_an_empty_or_missing_client_is_refused(self) -> None:
        """Supports: test_s3_names_an_empty_client.

        Given the walkthrough's command line with --client "", or without --client.
        When cli.main runs it.
        Then it names --client, reads no file, and gives 1.
        """
        for argv in (argv_with(client=""), argv_without("client")):
            with self.subTest(argv=argv):
                self.assert_refused(argv, "--client")

    def test_an_empty_or_missing_number_is_refused(self) -> None:
        """Supports: test_s3_names_an_empty_number.

        Given the walkthrough's command line with --number "", or without --number.
        When cli.main runs it.
        Then it names --number, reads no file, and gives 1.
        """
        for argv in (argv_with(number=""), argv_without("number")):
            with self.subTest(argv=argv):
                self.assert_refused(argv, "--number")

    def test_no_file_and_no_sample_is_refused(self) -> None:
        """Supports: test_s3_names_the_file_where_none_and_no_sample_are_given.

        Given no arguments, or the three values with no file.
        When cli.main runs it.
        Then it names the .ods file it needs, makes no sample, and gives 1.
        """
        for argv in ([], WALKTHROUGH_ARGS[1:]):
            with self.subTest(argv=argv):
                self.assert_refused(list(argv), ".ods")

    def test_the_sample_alone_is_made_and_printed(self) -> None:
        """Supports: test_s2_prints_the_sample.

        Given `--sample` alone.
        When cli.main runs it.
        Then it reads no file, has the sample made of its own lines dated today, at the
        fraction of its typed rate, shows it, has it printed, and gives 0.
        """
        code, out, _ = self.main(["--sample"])
        self.read.assert_not_called()
        lines, details, today = self.made()
        self.assertTrue(lines)
        self.assertTrue(details.client and details.number)
        self.assertEqual(details.rate, Decimal(details.rate_typed) / 100)
        self.assertEqual(today, date.today())
        self.send.assert_called_once_with(Invoice(TEXT))
        self.assertEqual(out.splitlines(), TEXT.splitlines() + ["", SENT])
        self.assertEqual(code, 0)

    def test_the_sample_with_a_file_is_refused(self) -> None:
        """Supports: test_s3_names_the_file_to_leave_out_beside_sample.

        Given `--sample October.ods`.
        When cli.main runs it.
        Then it names October.ods to leave out, makes nothing, and gives 1.
        """
        self.assert_refused(["--sample", "October.ods"], "October.ods")

    def test_the_sample_with_a_value_is_refused(self) -> None:
        """Supports: test_s3_names_the_value_to_leave_out_beside_sample.

        Given `--sample` with --client, --number, or --rate.
        When cli.main runs it.
        Then it names that option to leave out, makes nothing, and gives 1.
        """
        for option, value in (
            ("--client", "Nordwind GmbH"),
            ("--number", "2026-031"),
            ("--rate", "19"),
        ):
            with self.subTest(option=option):
                self.assert_refused(["--sample", option, value], option)

    def test_an_option_with_no_value_after_it_is_refused(self) -> None:
        """Supports: test_s3_names_the_value_before_reading_the_file.

        Given the walkthrough's command line ending with --rate, its value left out.
        When cli.main runs it.
        Then it names --rate, reads no file, and gives 1.
        """
        self.assert_refused(list(WALKTHROUGH_ARGS[:-1]), "--rate")

    def test_an_option_given_twice_is_refused(self) -> None:
        """Supports: test_s3_names_the_value_before_reading_the_file.

        Given the walkthrough's command line with --rate 7 after its --rate 19.
        When cli.main runs it.
        Then it names --rate, reads no file, and gives 1, taking neither rate.
        """
        self.assert_refused(list(WALKTHROUGH_ARGS) + ["--rate", "7"], "--rate")

    def test_an_option_that_invoicer_lacks_is_refused(self) -> None:
        """Supports: test_s3_names_the_value_before_reading_the_file.

        Given the walkthrough's command line with --rat 19 in place of --rate 19.
        When cli.main runs it.
        Then it names --rat, reads no file, and gives 1.
        """
        code, out, err = self.main(argv_without("rate") + ["--rat", "19"])
        self.assertRegex(out + err, r"--rat\b", "--rat is named, not only --rate")
        self.read.assert_not_called()
        self.make.assert_not_called()
        self.send.assert_not_called()
        self.assertEqual(code, 1)

    def test_the_values_are_checked_before_the_file_is_read(self) -> None:
        """Supports: test_s3_names_the_value_before_reading_the_file.

        Given a command line whose client is empty and whose rate is 119.
        When cli.main runs it.
        Then it refuses with 1 and never asks the reader for the file.
        """
        self.assert_refused(argv_with(client="", rate="119"))

    def test_the_readers_refusal_is_written_and_gives_1(self) -> None:
        """Supports: test_s3_names_the_row_of_a_price_that_isnt_a_number.

        Given a reader that refuses with `row 3: the price "14,50 EUR" isn't a number`.
        When cli.main runs the walkthrough's command line.
        Then it writes that refusal, makes and prints nothing, and gives 1.
        """
        fix = 'row 3: the price "14,50 EUR" isn\'t a number'
        self.read.side_effect = Refusal(fix)
        code, out, err = self.main(list(WALKTHROUGH_ARGS))
        self.assertIn(fix, out + err)
        self.make.assert_not_called()
        self.send.assert_not_called()
        self.assertEqual(code, 1)

    def test_the_printers_refusal_is_written_after_the_invoice_and_gives_1(
        self,
    ) -> None:
        """Supports: test_s1_names_lpstat_where_no_default_printer_is_set.

        Given a printer that refuses with its reason and `lpstat -d` to check.
        When cli.main runs the walkthrough's command line.
        Then it shows the invoice, writes the reason and the check in place of the line that it
        was sent, and gives 1.
        """
        self.send.side_effect = Refusal("No default printer is set.", check="lpstat -d")
        code, out, err = self.main(list(WALKTHROUGH_ARGS))
        self.assertIn(TEXT, out)
        self.assertIn("No default printer is set.", out + err)
        self.assertIn("lpstat -d", out + err)
        self.assertNotIn(SENT, out + err)
        self.assertEqual(code, 1)

    def test_the_invoice_shows_before_it_goes_to_the_printer(self) -> None:
        """Supports: test_s1_names_cups_client_where_lp_is_missing.

        Given a printer that looks at the terminal once it's handed the invoice.
        When cli.main runs the walkthrough's command line.
        Then the terminal already shows the invoice.
        """
        shown: list[str] = []
        self.send.side_effect = lambda _: shown.append(self.out.getvalue())
        self.main(list(WALKTHROUGH_ARGS))
        self.assertEqual(len(shown), 1)
        self.assertIn(TEXT, shown[0])

    def test_a_run_holds_only_its_own_values(self) -> None:
        """Supports: test_s1_keeps_nothing_of_one_invoice_for_the_next.

        Given a run for Nordwind GmbH at 19 that came first.
        When cli.main runs for Kauri Ltd, number 2026-032, at 7.
        Then its details hold only Kauri Ltd, 2026-032, and 7.
        """
        self.main(list(WALKTHROUGH_ARGS))
        self.main(argv_with(client="Kauri Ltd", number="2026-032", rate="7"))
        details = self.made()[1]
        self.assertEqual(
            details, Details("Kauri Ltd", "2026-032", "7", Decimal("0.07"))
        )


class RunTest(unittest.TestCase):
    """cli.run, the console script `invoicer`."""

    def test_the_console_script_exits_with_mains_status(self) -> None:
        """Supports: test_s1_prints_the_walkthrough_invoice.

        Given the command line `invoicer --sample`, and a main that gives 1.
        When the console script runs.
        Then main gets the arguments after `invoicer`, and the script exits with 1.
        """
        argv = mock.patch.object(sys, "argv", ["invoicer", "--sample"])
        with (
            mock.patch.object(cli, "main", return_value=1) as main,
            argv,
            self.assertRaises(SystemExit) as ended,
        ):
            cli.run()
        main.assert_called_once_with(["--sample"])
        self.assertEqual(ended.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
