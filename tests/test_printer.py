"""The unit cases of the printer: printer.send with a double of lp, and printer.lp with the stand-in.

Each docstring names, after Supports, the integration case of tests/test_integration.py that it
supports.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import unittest
from unittest import mock

from harness import Folder

from invoicer import printer
from invoicer.invoice import Invoice
from invoicer.refusal import Refusal

INVOICE = Invoice("Invoice 2026-031\nClient: Nordwind GmbH")
NO_DEFAULT = "lp: Error - no default destination available.\n"
NOT_ACCEPTING = 'lp: Error - Destination "Office" is not accepting jobs.\n'


def answer(code: int, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    """What lp gives back, as subprocess gives it."""
    return subprocess.CompletedProcess(["lp"], code, out, err)


class SendTest(unittest.TestCase):
    """printer.send, with a double in place of printer.lp."""

    def send(self, lp: mock.Mock) -> None:
        """printer.send of INVOICE, with `lp` in place of printer.lp, the terminal kept apart."""
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(printer, "lp", lp),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            try:
                printer.send(INVOICE)
            finally:
                self.assertEqual(
                    out.getvalue() + err.getvalue(), "", "only the command writes"
                )

    def refusal(self, lp: mock.Mock) -> Refusal:
        """The Refusal that printer.send raises with `lp` in place of printer.lp."""
        with self.assertRaises(Refusal) as refused:
            self.send(lp)
        return refused.exception

    def test_a_job_that_lp_takes_gives_nothing(self) -> None:
        """Supports: test_s1_prints_the_walkthrough_invoice.

        Given an lp that takes the job.
        When send hands it the invoice.
        Then lp gets the invoice's text once, and send refuses nothing.
        """
        lp = mock.Mock(return_value=answer(0, "request id is Office-17 (0 file(s))\n"))
        self.send(lp)
        lp.assert_called_once_with(INVOICE.text)

    def test_a_missing_lp_names_cups_client_to_install(self) -> None:
        """Supports: test_s1_names_cups_client_where_lp_is_missing.

        Given no lp on the path.
        When send hands it the invoice.
        Then it refuses, with cups-client to install as the Requirement to check.
        """
        refusal = self.refusal(mock.Mock(side_effect=FileNotFoundError("lp")))
        self.assertTrue(refusal.fix)
        self.assertIn("cups-client", refusal.check)

    def test_no_default_printer_names_lpstat_to_check(self) -> None:
        """Supports: test_s1_names_lpstat_where_no_default_printer_is_set.

        Given an lp that says no default destination is set.
        When send hands it the invoice.
        Then it refuses, with `lpstat -d` as the Requirement to check.
        """
        refusal = self.refusal(mock.Mock(return_value=answer(1, err=NO_DEFAULT)))
        self.assertTrue(refusal.fix)
        self.assertIn("lpstat -d", refusal.check)

    def test_a_refused_job_gives_cups_reason(self) -> None:
        """Supports: test_s1_gives_the_reason_where_the_printer_refuses.

        Given an lp that says the printer isn't accepting jobs.
        When send hands it the invoice.
        Then it refuses with CUPS's own reason, and a Requirement to check.
        """
        refusal = self.refusal(mock.Mock(return_value=answer(1, err=NOT_ACCEPTING)))
        self.assertIn('Destination "Office" is not accepting jobs', refusal.fix)
        self.assertTrue(refusal.check)


class LpTest(Folder):
    """printer.lp, with the stand-in lp of tests/bin first on the path."""

    def test_the_text_goes_to_lp_with_no_printer_named(self) -> None:
        """Supports: test_s1_sends_to_the_default_printer_with_none_named.

        Given a default printer that takes the job.
        When lp runs with the invoice's text.
        Then the stand-in gets the text on its input with no printer named, and lp gives its
        status 0 and its words.
        """
        done = printer.lp(INVOICE.text)
        jobs = self.jobs()
        self.assertEqual([job["input"] for job in jobs], [INVOICE.text])
        self.assertFalse(
            [arg for arg in jobs[0]["args"] if arg.startswith(("-d", "-P"))]
        )
        self.assertEqual(done.returncode, 0)
        self.assertIn("request id is", done.stdout)

    def test_cups_words_come_back_as_they_are(self) -> None:
        """Supports: test_s1_names_lpstat_where_no_default_printer_is_set.

        Given CUPS with no default printer set, or a printer that refuses.
        When lp runs with the invoice's text.
        Then it gives lp's non-zero status and CUPS's own words, and raises nothing.
        """
        for state, words in (("no-default", NO_DEFAULT), ("refuses", NOT_ACCEPTING)):
            with self.subTest(state=state):
                self.printer_answers(state)
                done = printer.lp(INVOICE.text)
                self.assertNotEqual(done.returncode, 0)
                self.assertEqual(done.stderr, words)

    def test_a_missing_lp_raises_file_not_found(self) -> None:
        """Supports: test_s1_names_cups_client_where_lp_is_missing.

        Given no lp on the path.
        When lp runs with the invoice's text.
        Then it raises FileNotFoundError.
        """
        self.without_lp()
        with self.assertRaises(FileNotFoundError):
            printer.lp(INVOICE.text)


if __name__ == "__main__":
    unittest.main()
