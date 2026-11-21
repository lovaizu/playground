"""取引日と支払条件から、締めの期間と発行日と支払期限をどう決めるか。"""

from __future__ import annotations

import calendar
import datetime
from dataclasses import dataclass

from invoice.issuer import Day, PaymentTerms


@dataclass(frozen=True)
class Period:
    """締めの期間: 前の締め日の翌日から、次の締め日まで (P3.7)。"""

    start: datetime.date
    """期間の最初の日。"""
    end: datetime.date
    """締め日。"""


@dataclass(frozen=True)
class Dates:
    """一枚の請求書の日付: 締めの期間、発行日、支払期限。"""

    period: Period
    """締めの期間。"""
    issue_date: datetime.date
    """発行日。締めの期間の締め日 (P3.6)。"""
    due_date: datetime.date
    """支払期限 (P3.9)。"""


def dates_of(day: datetime.date, terms: PaymentTerms) -> Dates:
    """取引日を含む締めの期間と、その請求書の発行日と支払期限。

    受け取る: 明細行の取引日と、発行者情報の支払条件。
    返す: 取引日を含む締めの期間と、その発行日と支払期限 (P3.6 から P3.9)。
        締め日は、取引日の月の締め日か、取引日がそれより後なら翌月の締め日。
        期間は、その一つ前の月の締め日の翌日から始まる。
        支払期限は、締め日の月から支払の月だけ進めた月の支払日。
        同じ期間に入る取引日には、同じ値を返す。
    ほかに変えるもの: なし。
    断るとき: なし。支払条件は issuer.check が確かめ終えている。
    """
    month = _month_index(day)
    if day > _on(month, terms.closing_day):
        month += 1
    end = _on(month, terms.closing_day)
    start = _on(month - 1, terms.closing_day) + datetime.timedelta(days=1)
    due = _on(month + terms.month, terms.payment_day)
    return Dates(period=Period(start=start, end=end), issue_date=end, due_date=due)


def _month_index(day: datetime.date) -> int:
    """月を、紀元からの通しの数で。月を足し引きできるようにするため。"""
    return day.year * 12 + day.month - 1


def _on(month: int, day: Day) -> datetime.date:
    """通しの数の月の、締め日か支払日。"""
    year, index = divmod(month, 12)
    last = calendar.monthrange(year, index + 1)[1]
    return datetime.date(year, index + 1, last if day == "month_end" else day)
