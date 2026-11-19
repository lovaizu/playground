"""The unit cases of the refusal, Refusal.

Each docstring names, after Supports, the integration case of tests/test_integration.py that it
supports.
"""

from __future__ import annotations

import unittest

from invoicer.refusal import Refusal

FIX = 'row 3: the price "14,50 EUR" isn\'t a number'


class RefusalTest(unittest.TestCase):
    """Refusal, which the command, the reader, and the printer raise."""

    def test_a_refusal_holds_what_to_fix_and_no_check(self) -> None:
        """Supports: test_s3_names_the_row_of_a_price_that_isnt_a_number.

        Given what to fix alone.
        When a Refusal is raised with it.
        Then it holds that fix, says it as its message, and has no Requirement to check.
        """
        self.assertTrue(issubclass(Refusal, Exception))
        with self.assertRaises(Refusal) as raised:
            raise Refusal(FIX)
        self.assertEqual(
            (raised.exception.fix, raised.exception.check, str(raised.exception)),
            (FIX, "", FIX),
        )

    def test_a_refusal_holds_the_printers_reason_and_the_check(self) -> None:
        """Supports: test_s1_names_lpstat_where_no_default_printer_is_set.

        Given the printer's reason and `lpstat -d`.
        When a Refusal is made of them.
        Then it holds the reason as its fix and `lpstat -d` as its check.
        """
        refusal = Refusal("No default printer is set.", check="lpstat -d")
        self.assertEqual(
            (refusal.fix, refusal.check), ("No default printer is set.", "lpstat -d")
        )


if __name__ == "__main__":
    unittest.main()
