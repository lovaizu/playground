"""請求書の額を、消費税と合計の決まりに沿ってどう出すか。"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

from invoice import numbering, periods
from invoice.issuer import Issuer
from invoice.ledger import Customer, LedgerRow, TaxRate
from invoice.periods import Period


@dataclass(frozen=True)
class InvoiceLine:
    """請求書の明細の一行: 一つの明細行と、その金額。"""

    row: LedgerRow
    """明細行。取引日、品目、数量、単位、単価、税率はこのまま載せる。"""
    amount: int
    """金額。数量と単価の積の円の整数で、単価と同じく税込か税抜 (P3.2)。"""


@dataclass(frozen=True)
class RateTotal:
    """税率ごとの合計: 一枚の請求書の中の一つの税率の、対象額と消費税額。"""

    rate: TaxRate
    """税率。"""
    base: int
    """税率ごとの対象額。円の整数。税込か税抜は、請求書の tax_included のとおり。"""
    tax: int
    """消費税額。円未満を一度だけ切り捨てた円の整数 (P3.2)。"""


@dataclass(frozen=True)
class Invoice:
    """請求書: 一つの取引先の一つの締めの期間に請求する額と、その内訳。"""

    number: str
    """請求書番号 (P3.5)。"""
    customer: Customer
    """宛先の取引先。名称と敬称。"""
    period: Period
    """締めの期間。"""
    issue_date: datetime.date
    """発行日。periods.dates_of が決めたもの。"""
    due_date: datetime.date
    """支払期限。periods.dates_of が決めたもの。"""
    issuer: Issuer
    """発行者として載せる発行者情報。お振込先を含む。"""
    tax_included: bool
    """明細の単価が税込なら True、税抜なら False (P3.3)。"""
    lines: tuple[InvoiceLine, ...]
    """明細に載せる行と金額。取引日が締めの期間に入る明細行を、取引日の順に。
    同じ取引日の行は、明細の順のまま (P3.8)。"""
    totals: tuple[RateTotal, ...]
    """税率ごとの合計。明細にある税率ごとに一つずつ、10% を先に、8% をあとに。"""
    amount: int
    """請求額。税込の円の整数。ご請求金額と合計(税込)に載せる。"""


_RATES: tuple[TaxRate, ...] = (10, 8)
"""税率ごとの合計に載せる税率を、載せる順に。"""


def bill(rows: Sequence[LedgerRow], issuer: Issuer) -> tuple[Invoice, ...]:
    """請求書にさせる (S1)。

    受け取る: 直すところのない明細行と、発行者情報。単価の税込か税抜は、すべての行で同じ。
    返す: 取引先と締めの期間ごとに一枚ずつの請求書 (P3.4)。
        請求書の順は、最も早い取引日の順で、同じ日なら明細で先に出る取引先の順。
        日付は periods.dates_of に、番号は numbering.number に、
        取引先の名称を渡して、この順に求める。
        各行の金額、税率ごとの対象額と消費税額、請求額を決めるのは、
        このモジュールだけ (P3.1)。
    ほかに変えるもの: 番号の採番を通して、発行記録に番号を残させる。
    断るとき:
        place.StoreRefused: numbering.number が断ったとき、そのまま上げる。
    """
    groups: dict[tuple[Customer, periods.Dates], list[LedgerRow]] = {}
    for row in sorted(rows, key=lambda each: each.date):
        groups.setdefault((row.customer, periods.dates_of(row.date, issuer.payment_terms)), []).append(row)
    return tuple(_invoice(customer, dates, group, issuer) for (customer, dates), group in groups.items())


def _invoice(customer: Customer, dates: periods.Dates, rows: list[LedgerRow], issuer: Issuer) -> Invoice:
    tax_included = rows[0].tax_included
    lines = tuple(InvoiceLine(row, row.quantity * row.unit_price) for row in rows)
    totals = tuple(_total(rate, lines, tax_included) for rate in _RATES if any(row.tax_rate == rate for row in rows))
    taxes = 0 if tax_included else sum(total.tax for total in totals)
    return Invoice(
        number=numbering.number(customer.name, dates.period),
        customer=customer,
        period=dates.period,
        issue_date=dates.issue_date,
        due_date=dates.due_date,
        issuer=issuer,
        tax_included=tax_included,
        lines=lines,
        totals=totals,
        amount=sum(total.base for total in totals) + taxes,
    )


def _total(rate: TaxRate, lines: tuple[InvoiceLine, ...], tax_included: bool) -> RateTotal:
    """一つの税率の対象額と、その対象額から一度だけ切り捨てた消費税額 (P3.2, P3.3)。"""
    base = sum(line.amount for line in lines if line.row.tax_rate == rate)
    return RateTotal(rate, base, base * rate // (100 + rate if tax_included else 100))
