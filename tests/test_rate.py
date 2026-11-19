"""Unit cases of rate.parse_rate: each class of typed percent it takes or refuses, and the ends of
0 to 100."""

import unittest
from decimal import Decimal

from invoicer import rate


class TakesThePercent(unittest.TestCase):
    def assertRate(self, text, expected):
        got = rate.parse_rate(text)
        self.assertIsInstance(got, Decimal)
        self.assertEqual(got, Decimal(expected))

    def test_whole_percent(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the typed percent `19`.
        When parse_rate reads it.
        Then the rate is Decimal 0.19."""
        self.assertRate("19", "0.19")

    def test_percent_with_its_sign(self):
        """Supports: PrintsTheInvoice.test_page_the_printer_gets_is_made_from_the_sheets_details_lines_and_rate

        Given the typed percent `19%`.
        When parse_rate reads it.
        Then the rate is Decimal 0.19."""
        self.assertRate("19%", "0.19")

    def test_percent_with_a_space_before_its_sign(self):
        """Supports: PrintsTheInvoice.test_rate_typed_with_a_comma_a_point_or_a_sign_prints_at_that_rate

        Given the typed percent `19 %`, as German writes a percent.
        When parse_rate reads it.
        Then the rate is Decimal 0.19."""
        self.assertRate("19 %", "0.19")

    def test_percent_with_a_decimal_comma(self):
        """Supports: PrintsTheInvoice.test_rate_typed_with_a_comma_a_point_or_a_sign_prints_at_that_rate

        Given the typed percent `19,5`, with the decimal comma German accounting types.
        When parse_rate reads it.
        Then the rate is exactly Decimal 0.195."""
        self.assertRate("19,5", "0.195")

    def test_percent_with_a_decimal_point(self):
        """Supports: PrintsTheInvoice.test_rate_typed_with_a_comma_a_point_or_a_sign_prints_at_that_rate

        Given the typed percent `19.5`.
        When parse_rate reads it.
        Then the rate is exactly Decimal 0.195."""
        self.assertRate("19.5", "0.195")

    def test_percent_with_a_decimal_comma_and_its_sign(self):
        """Supports: PrintsTheInvoice.test_rate_typed_with_a_comma_a_point_or_a_sign_prints_at_that_rate

        Given the typed percent `7,5 %`.
        When parse_rate reads it.
        Then the rate is exactly Decimal 0.075."""
        self.assertRate("7,5 %", "0.075")

    def test_fraction_of_a_percent(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the typed percent `7.5`.
        When parse_rate reads it.
        Then the rate is exactly Decimal 0.075."""
        self.assertRate("7.5", "0.075")

    def test_zero_is_the_lowest(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the typed percent `0`, for a client who pays no tax.
        When parse_rate reads it.
        Then the rate is 0."""
        self.assertRate("0", "0")

    def test_one_is_the_lowest_above_zero(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the typed percent `1`, the lowest taken after 0.
        When parse_rate reads it.
        Then the rate is Decimal 0.01."""
        self.assertRate("1", "0.01")

    def test_zero_typed_with_a_minus_is_zero(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the typed percent `-0`.
        When parse_rate reads it.
        Then the rate is 0 with no sign, so the page reads `Tax 0%`."""
        got = rate.parse_rate("-0")

        self.assertEqual(str(got), "0.00")

    def test_hundred_is_the_highest(self):
        """Supports: PrintsTheInvoice.test_prints_the_sheets_invoice_at_the_typed_rate

        Given the typed percent `100`.
        When parse_rate reads it.
        Then the rate is 1."""
        self.assertRate("100", "1")


class RefusesThePercent(unittest.TestCase):
    def assertRefuses(self, text, message):
        with self.assertRaises(rate.RateError) as refused:
            rate.parse_rate(text)
        self.assertEqual(str(refused.exception), message)

    def test_empty(self):
        """Supports: RefusesWhatIsWrong.test_wrong_rate_is_refused_before_anything_is_printed

        Given nothing typed.
        When parse_rate reads it.
        Then it refuses, saying the empty rate isn't a number and to type a percent."""
        self.assertRefuses(
            "",
            "the rate `` isn't a number: type the client's tax rate as a percent from 0 to 100, "
            "such as --rate 19",
        )

    def test_not_a_number(self):
        """Supports: RefusesWhatIsWrong.test_wrong_rate_is_refused_before_anything_is_printed

        Given the typed text `nineteen`.
        When parse_rate reads it.
        Then it refuses, saying `nineteen` isn't a number and to type a percent."""
        self.assertRefuses(
            "nineteen",
            "the rate `nineteen` isn't a number: type the client's tax rate as a percent from 0 "
            "to 100, such as --rate 19",
        )

    def test_sign_alone(self):
        """Supports: RefusesWhatIsWrong.test_wrong_rate_is_refused_before_anything_is_printed

        Given the typed text `%`, with no number before it.
        When parse_rate reads it.
        Then it refuses, saying `%` isn't a number."""
        self.assertRefuses(
            "%",
            "the rate `%` isn't a number: type the client's tax rate as a percent from 0 to 100, "
            "such as --rate 19",
        )

    def test_not_a_number_that_decimal_reads(self):
        """Supports: RefusesWhatIsWrong.test_wrong_rate_is_refused_before_anything_is_printed

        Given the typed text `NaN`, which Python's Decimal reads as a value.
        When parse_rate reads it.
        Then it refuses, saying `NaN` isn't a number."""
        self.assertRefuses(
            "NaN",
            "the rate `NaN` isn't a number: type the client's tax rate as a percent from 0 to "
            "100, such as --rate 19",
        )

    def test_number_with_a_plus_sign(self):
        """Supports: RefusesWhatIsWrong.test_wrong_rate_is_refused_before_anything_is_printed

        Given the typed text `+19`, a form that no rate case names.
        When parse_rate reads it.
        Then it refuses, saying `+19` isn't a number."""
        self.assertRefuses(
            "+19",
            "the rate `+19` isn't a number: type the client's tax rate as a percent from 0 to "
            "100, such as --rate 19",
        )

    def test_just_below_zero(self):
        """Supports: RefusesWhatIsWrong.test_wrong_rate_is_refused_before_anything_is_printed

        Given the typed percent `-0.01`.
        When parse_rate reads it.
        Then it refuses, saying it's outside 0 to 100."""
        self.assertRefuses(
            "-0.01",
            "the rate `-0.01` is outside 0 to 100: type the client's tax rate as a percent from 0 "
            "to 100, such as --rate 19",
        )

    def test_just_above_hundred(self):
        """Supports: RefusesWhatIsWrong.test_rate_is_read_before_the_sheet

        Given the typed percent `100.01`.
        When parse_rate reads it.
        Then it refuses, saying it's outside 0 to 100."""
        self.assertRefuses(
            "100.01",
            "the rate `100.01` is outside 0 to 100: type the client's tax rate as a percent from "
            "0 to 100, such as --rate 19",
        )

    def test_slip_far_above_hundred(self):
        """Supports: RefusesWhatIsWrong.test_rate_is_read_before_the_sheet

        Given the typed percent `190`, a slip for 19.
        When parse_rate reads it.
        Then it refuses, saying it's outside 0 to 100."""
        self.assertRefuses(
            "190",
            "the rate `190` is outside 0 to 100: type the client's tax rate as a percent from 0 "
            "to 100, such as --rate 19",
        )

    def test_fraction_typed_for_a_percent(self):
        """Supports: RefusesWhatIsWrong.test_rate_typed_as_a_fraction_is_refused

        Given the typed rate `0.19`, the fraction of 19% typed for the percent.
        When parse_rate reads it.
        Then it refuses, saying to type the rate as a percent, such as 19 for 19%."""
        self.assertRefuses(
            "0.19", "the rate `0.19` is below 1%: type the rate as a percent, such as 19 for 19%"
        )

    def test_just_above_zero_is_a_fraction(self):
        """Supports: RefusesWhatIsWrong.test_rate_typed_as_a_fraction_is_refused

        Given the typed rate `0,01`, the least more than 0 of two decimals.
        When parse_rate reads it.
        Then it refuses, saying to type the rate as a percent."""
        self.assertRefuses(
            "0,01", "the rate `0,01` is below 1%: type the rate as a percent, such as 19 for 19%"
        )

    def test_just_below_one_is_a_fraction(self):
        """Supports: RefusesWhatIsWrong.test_rate_typed_as_a_fraction_is_refused

        Given the typed rate `0.99`, the most below 1 of two decimals.
        When parse_rate reads it.
        Then it refuses, saying to type the rate as a percent."""
        self.assertRefuses(
            "0.99", "the rate `0.99` is below 1%: type the rate as a percent, such as 19 for 19%"
        )


if __name__ == "__main__":
    unittest.main()
