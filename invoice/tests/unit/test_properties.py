"""invoice の要件から取った、使い方がもたらすどの入力にも成り立つ決まりのプロパティ。"""

from __future__ import annotations

import calendar
import random
import tempfile
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from invoice import billing, issuer, ledger, numbering, periods
from invoice.billing import Invoice
from invoice.issuer import BankAccount, Day, Issuer, PaymentTerms
from invoice.ledger import Customer, LedgerRow
from invoice.periods import Dates, Period
from tests.given import AOBA, ITEMS, csv, fresh_home

supports = pytest.mark.supports

ONE_DAY = timedelta(days=1)
MONTHS = ("当月", "翌月", "翌々月")
DAYS: st.SearchStrategy[Day] = st.one_of(st.integers(1, 28), st.just("month_end"))
"""受け付ける締め日と支払日 (P3.12)。"""


def accepted(terms: PaymentTerms) -> bool:
    """当月払いは支払日が締め日より後のときだけ受け付ける (P3.11)。"""
    if terms.month != 0:
        return True
    if terms.closing_day == "month_end":
        return False
    return terms.payment_day == "month_end" or terms.payment_day > terms.closing_day


TERMS = st.builds(PaymentTerms, DAYS, st.sampled_from((0, 1, 2)), DAYS).filter(accepted)
"""受け付ける支払条件。"""

DAYS_OF_USE = st.dates(date(2000, 1, 1), date(2099, 12, 31))
"""明細の取引日。"""


def said(terms: PaymentTerms) -> str:
    """支払条件を、利用者が答える「20日締め翌月10日払い」の形で (P3.10)。"""
    closing = "月末" if terms.closing_day == "month_end" else f"{terms.closing_day}日"
    payment = "末" if terms.payment_day == "month_end" else f"{terms.payment_day}日"
    return f"{closing}締め{MONTHS[terms.month]}{payment}払い"


def on(year: int, month: int, day: Day) -> date:
    return date(year, month, calendar.monthrange(year, month)[1] if day == "month_end" else day)


def shifted(year: int, month: int, months: int) -> tuple[int, int]:
    index = year * 12 + month - 1 + months
    return index // 12, index % 12 + 1


def model(day: date, terms: PaymentTerms) -> Dates:
    """P3.6 から P3.9 をそのまま書いた、締めの期間と発行日と支払期限のモデル。"""
    year, month = day.year, day.month
    end = on(year, month, terms.closing_day)
    if day > end:
        year, month = shifted(year, month, 1)
        end = on(year, month, terms.closing_day)
    before = on(*shifted(year, month, -1), terms.closing_day)
    due = on(*shifted(year, month, terms.month), terms.payment_day)
    return Dates(period=Period(start=before + ONE_DAY, end=end), issue_date=end, due_date=due)


CUSTOMERS = (
    Customer("株式会社みなと商事", "御中"),
    Customer("株式会社みなと商事東京支店", "御中"),
    Customer("株式会社ひかり設計", "御中"),
)


@st.composite
def ledger_rows(draw: st.DrawFn) -> tuple[LedgerRow, ...]:
    """一つの明細の、取引先と取引日と税率の入り混じった明細行。単価は明細の全体で税込か税抜。"""
    included = draw(st.booleans())
    cells = draw(
        st.lists(
            st.tuples(
                st.sampled_from(CUSTOMERS),
                st.dates(date(2026, 10, 1), date(2026, 12, 31)),
                st.integers(1, 9999),
                st.integers(1, 10_000_000),
                st.sampled_from((8, 10)),
            ),
            min_size=1,
            max_size=40,
        )
    )
    return tuple(
        LedgerRow(i + 2, customer, day, f"品目 {i}", quantity, "個", price, rate, included)  # type: ignore[arg-type]
        for i, (customer, day, quantity, price, rate) in enumerate(cells)
    )


def model_bill(rows: Sequence[LedgerRow], terms: PaymentTerms) -> dict[tuple[str, Period], dict[str, object]]:
    """P3.2 から P3.4 と P3.8 をそのまま書いた、取引先と期間ごとの請求書の額のモデル。

    明細の行は、取引日の順に、同じ日は明細の順のまま並ぶ。
    """
    groups: dict[tuple[str, Period], list[LedgerRow]] = {}
    for each in sorted(rows, key=lambda row: row.date):
        groups.setdefault((each.customer.name, model(each.date, terms).period), []).append(each)
    found = {}
    for key, group in groups.items():
        bases: dict[int, int] = {}
        for each in group:
            bases[each.tax_rate] = bases.get(each.tax_rate, 0) + each.quantity * each.unit_price
        included = group[0].tax_included
        taxes = {rate: base * rate // (100 + rate if included else 100) for rate, base in bases.items()}
        found[key] = {
            "lines": [(each, each.quantity * each.unit_price) for each in group],
            "totals": {rate: (bases[rate], taxes[rate]) for rate in bases},
            "amount": sum(bases.values()) + (0 if included else sum(taxes.values())),
        }
    return found


def summary(invoices: Sequence[Invoice]) -> dict[tuple[str, Period], dict[str, object]]:
    return {
        (each.customer.name, each.period): {
            "lines": [(line.row, line.amount) for line in each.lines],
            "totals": {total.rate: (total.base, total.tax) for total in each.totals},
            "amount": each.amount,
        }
        for each in invoices
    }


@supports("P3.6", "P3.7", "P3.9")
@given(day=DAYS_OF_USE, terms=TERMS)
def test_締めの期間と発行日と支払期限は支払条件のとおりに決まる(day: date, terms: PaymentTerms) -> None:
    """モデルに基づくプロパティ。"""
    # Given any: 取引日と、受け付ける支払条件。
    # When
    dates = periods.dates_of(day, terms)
    # Then
    assert dates == model(day, terms)


@supports("P3.7", "P3.8")
@given(day=DAYS_OF_USE, terms=TERMS)
def test_取引日は締めの期間に入り期間は隙間なく続く(day: date, terms: PaymentTerms) -> None:
    """不変条件と帰納のプロパティ。"""
    # Given any: 取引日と、受け付ける支払条件。
    # When
    period = periods.dates_of(day, terms).period
    after = periods.dates_of(period.end + ONE_DAY, terms).period
    # Then
    assert period.start <= day <= period.end
    assert periods.dates_of(period.start, terms).period == period
    assert after.start == period.end + ONE_DAY


@supports("P3.10", "P3.11", "P3.12")
@given(
    closing=st.one_of(st.integers(0, 31), st.just("month_end")),
    month=st.sampled_from((0, 1, 2)),
    payment=st.one_of(st.integers(0, 31), st.just("month_end")),
)
def test_形どおりで範囲に入る支払条件だけが三つの値に読み取られる(closing: Day, month: int, payment: Day) -> None:
    """モデルに基づくプロパティ。"""
    # Given any: 利用者が「20日締め翌月10日払い」の形で答える支払条件。
    terms = PaymentTerms(closing, month, payment)  # type: ignore[arg-type]
    answer = said(terms)
    in_range = all(each == "month_end" or 1 <= each <= 28 for each in (closing, payment))
    # When / Then
    if in_range and accepted(terms):
        assert issuer.check("payment_terms", answer) == terms
    else:
        with pytest.raises(issuer.AnswerRefused) as refused:
            issuer.check("payment_terms", answer)
        assert (refused.value.fix.item, refused.value.fix.given) == ("payment_terms", answer)


@supports("P3.2", "P3.3", "P3.4", "P3.8", "請求の計算")
@given(rows=ledger_rows(), terms=TERMS)
def test_請求書の額は取引先と期間ごとに税率ごとの対象額から一度だけ切り捨てて出る(
    rows: tuple[LedgerRow, ...], terms: PaymentTerms
) -> None:
    """モデルに基づくプロパティ。"""
    # Given any: 一つの明細の明細行と、受け付ける支払条件。
    issuer_info = Issuer(AOBA.name, AOBA.registration_number, terms, AOBA.bank)
    # When
    with fresh_home():
        invoices = billing.bill(rows, issuer_info)
    # Then
    assert len(invoices) == len(summary(invoices))
    assert summary(invoices) == model_bill(rows, terms)


@supports("P3.4", "明細行")
@given(rows=ledger_rows(), seed=st.integers())
def test_明細の行の順を入れ替えても取引先と期間ごとの額は変わらない(rows: tuple[LedgerRow, ...], seed: int) -> None:
    """メタモルフィックなプロパティ。"""
    # Given any: 一つの明細の明細行と、その順を入れ替えた明細行。
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    # When
    with fresh_home():
        first = billing.bill(rows, AOBA)
    with fresh_home():
        second = billing.bill(shuffled, AOBA)

    # Then
    def amounts(invoices: Sequence[Invoice]) -> dict[tuple[str, Period], tuple[int, frozenset[object]]]:
        return {(each.customer.name, each.period): (each.amount, frozenset(each.totals)) for each in invoices}

    assert amounts(first) == amounts(second)


@supports("P1.4", "P3.5")
@given(rows=ledger_rows())
def test_同じ明細行を打ち直すと前と同じ請求書が出る(rows: tuple[LedgerRow, ...]) -> None:
    """メタモルフィックなプロパティ。"""
    # Given any: 一度請求書にさせた明細行。
    with fresh_home():
        first = billing.bill(rows, AOBA)
        # When
        second = billing.bill(rows, AOBA)
    # Then
    assert set(second) == set(first)


PERIODS = (
    Period(date(2026, 10, 1), date(2026, 10, 31)),
    Period(date(2026, 11, 1), date(2026, 11, 30)),
    Period(date(2026, 10, 21), date(2026, 11, 20)),
)


@supports("P3.5", "発行記録")
@given(
    requests=st.lists(
        st.tuples(st.sampled_from([each.name for each in CUSTOMERS]), st.sampled_from(PERIODS)),
        min_size=1,
        max_size=20,
    )
)
def test_同じ組には同じ番号を別の組には別の番号を付ける(requests: list[tuple[str, Period]]) -> None:
    """モデルに基づくプロパティ。モデルは、組から初めに付けた番号への辞書。"""
    # Given any: 取引先と締めの期間の組を、繰り返しも含めて並べた求め。
    # When
    with fresh_home():
        numbers = [numbering.number(customer, period) for customer, period in requests]
    # Then
    first: dict[tuple[str, Period], str] = {}
    for pair, number in zip(requests, numbers, strict=True):
        assert number == first.setdefault(pair, number)
    assert len(set(first.values())) == len(first)


REFUSED = {"取引日": "2026-11-31", "数量": "十", "単価(税抜)": "二千八百", "税率": "5%"}
COLUMNS = ("取引先", "取引日", "品目", "数量", "単位", "単価(税抜)", "税率")


@supports("P1.3", "直すところ")
@given(data=st.data())
def test_明細の誤りはすべての行を読んでから一度に示される(data: st.DataObject) -> None:
    """モデルに基づくプロパティ。モデルは、誤りを入れた行と列の集まり。"""
    # Given any: 何行かの明細と、そのどこかの列に入れた、受け付けない値。
    count = data.draw(st.integers(1, 30))
    broken = data.draw(st.sets(st.tuples(st.integers(0, count - 1), st.sampled_from(tuple(REFUSED))), min_size=1))
    rows = []
    for i in range(count):
        cells = ["株式会社みなと商事", "2026-11-05", "コピー用紙 A4 500枚", "10", "箱", "2800", "10%"]
        for at, column in broken:
            if at == i:
                cells[COLUMNS.index(column)] = REFUSED[column]
        rows.append(",".join(cells))
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "明細.csv"
        path.write_text(csv(*rows), encoding="utf-8")
        # When
        with pytest.raises(ledger.LedgerRefused) as refused:
            ledger.read(path)
    # Then
    assert sorted((fix.problem, fix.line, fix.column, fix.given) for fix in refused.value.fixes) == sorted(
        ("bad_value", at + 2, column, REFUSED[column]) for at, column in broken
    )


WIDTH_FORMS = "".join(chr(code) for code in range(0xFF01, 0xFFA0))
"""読み替える全角の英数字と記号、半角カナ。読み替えは test_width.py と test_issuer.py が確かめる。"""
TEXT = st.text(st.characters(categories=("L", "N"), exclude_characters=WIDTH_FORMS), min_size=1, max_size=30)
"""読み替えずにそのまま残る、利用者が答える名前。"""
KANA = (
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
    "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポー"
)
HOLDERS = st.builds(
    lambda prefix, name: prefix + name,
    st.sampled_from(("", "カ)", "ユ)")),
    st.text(st.sampled_from(KANA), min_size=1, max_size=20),
)


@supports("P2.2", "P2.4", "発行者情報")
@given(
    name=TEXT,
    number=st.from_regex(r"T[0-9]{13}", fullmatch=True),
    terms=TERMS,
    bank=TEXT,
    branch=TEXT,
    kind=st.sampled_from(("普通", "当座")),
    account=st.from_regex(r"[0-9]{7}", fullmatch=True),
    holder=HOLDERS,
)
def test_そろった答えで残した発行者情報は次に読み直しても同じ(
    name: str, number: str, terms: PaymentTerms, bank: str, branch: str, kind: str, account: str, holder: str
) -> None:
    """不変条件のプロパティ。"""
    # Given any: 利用者がそろえて答えた、形に合う発行者の情報。
    answers = dict(zip(ITEMS, (name, number, said(terms), bank, branch, kind, account, holder), strict=True))
    with fresh_home():
        # When
        saved = issuer.save({item: issuer.check(item, answer) for item, answer in answers.items()})
        loaded = issuer.load()
    # Then
    assert loaded == saved == Issuer(name, number, terms, BankAccount(bank, branch, kind, account, holder))  # type: ignore[arg-type]
