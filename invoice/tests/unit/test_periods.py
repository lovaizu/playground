"""締めの期間と日付 (periods.dates_of) の単体ケース。"""

from __future__ import annotations

from datetime import date

import pytest

from invoice import periods
from invoice.issuer import PaymentTerms
from invoice.periods import Dates, Period

supports = pytest.mark.supports

ON_20_NEXT_10 = PaymentTerms(20, 1, 10)
END_NEXT_END = PaymentTerms("month_end", 1, "month_end")


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
@pytest.mark.parametrize(
    ("day", "terms", "start", "end", "due"),
    [
        (date(2026, 11, 5), ON_20_NEXT_10, date(2026, 10, 21), date(2026, 11, 20), date(2026, 12, 10)),
        (date(2026, 11, 20), ON_20_NEXT_10, date(2026, 10, 21), date(2026, 11, 20), date(2026, 12, 10)),
        (date(2026, 11, 21), ON_20_NEXT_10, date(2026, 11, 21), date(2026, 12, 20), date(2027, 1, 10)),
        (date(2026, 10, 21), ON_20_NEXT_10, date(2026, 10, 21), date(2026, 11, 20), date(2026, 12, 10)),
        (date(2026, 11, 5), END_NEXT_END, date(2026, 11, 1), date(2026, 11, 30), date(2026, 12, 31)),
        (date(2026, 11, 30), END_NEXT_END, date(2026, 11, 1), date(2026, 11, 30), date(2026, 12, 31)),
        (date(2026, 12, 1), END_NEXT_END, date(2026, 12, 1), date(2026, 12, 31), date(2027, 1, 31)),
        (date(2027, 1, 15), END_NEXT_END, date(2027, 1, 1), date(2027, 1, 31), date(2027, 2, 28)),
        (date(2028, 1, 31), END_NEXT_END, date(2028, 1, 1), date(2028, 1, 31), date(2028, 2, 29)),
        (date(2028, 2, 28), PaymentTerms(28, 1, 10), date(2028, 1, 29), date(2028, 2, 28), date(2028, 3, 10)),
        (date(2028, 2, 29), PaymentTerms(28, 1, 10), date(2028, 2, 29), date(2028, 3, 28), date(2028, 4, 10)),
        (date(2026, 3, 1), PaymentTerms(28, 1, 10), date(2026, 3, 1), date(2026, 3, 28), date(2026, 4, 10)),
        (date(2026, 11, 5), PaymentTerms(10, 0, 25), date(2026, 10, 11), date(2026, 11, 10), date(2026, 11, 25)),
        (
            date(2026, 11, 5),
            PaymentTerms(10, 0, "month_end"),
            date(2026, 10, 11),
            date(2026, 11, 10),
            date(2026, 11, 30),
        ),
        (date(2026, 12, 25), PaymentTerms(20, 2, 10), date(2026, 12, 21), date(2027, 1, 20), date(2027, 3, 10)),
        (
            date(2026, 12, 31),
            PaymentTerms("month_end", 2, "month_end"),
            date(2026, 12, 1),
            date(2026, 12, 31),
            date(2027, 2, 28),
        ),
        (date(2026, 11, 1), PaymentTerms(1, 1, 1), date(2026, 10, 2), date(2026, 11, 1), date(2026, 12, 1)),
        (date(2026, 11, 2), PaymentTerms(1, 1, 1), date(2026, 11, 2), date(2026, 12, 1), date(2027, 1, 1)),
        (date(2026, 1, 31), PaymentTerms("month_end", 1, 28), date(2026, 1, 1), date(2026, 1, 31), date(2026, 2, 28)),
    ],
)
def test_取引日を含む締めの期間と締め日の発行日と支払条件どおりの支払期限を返す(
    day: date, terms: PaymentTerms, start: date, end: date, due: date
) -> None:
    # Given: 取引日と、確かめ終えた支払条件。
    # When
    dates = periods.dates_of(day, terms)
    # Then
    assert dates == Dates(period=Period(start=start, end=end), issue_date=end, due_date=due)


@supports("test_支払条件は三つの値で保たれ期間と期限はその値から決まる")
def test_同じ期間に入る取引日には同じ値を返す() -> None:
    # Given: 同じ締めの期間の最初の日と締め日。
    # When
    first = periods.dates_of(date(2026, 10, 21), ON_20_NEXT_10)
    last = periods.dates_of(date(2026, 11, 20), ON_20_NEXT_10)
    # Then
    assert first == last
