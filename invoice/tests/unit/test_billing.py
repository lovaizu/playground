"""請求の計算 (billing.bill) の単体ケース。"""

from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path

import pytest

from invoice import billing, numbering, place
from invoice.billing import Invoice, InvoiceLine, RateTotal
from invoice.issuer import PaymentTerms
from invoice.ledger import Customer
from invoice.periods import Period
from tests.given import AOBA, MINATO, NOVEMBER, README_INVOICE, README_LEDGER_ROWS, files, row

supports = pytest.mark.supports

HIKARI = Customer("株式会社ひかり設計", "御中")
MINATO_TOKYO = Customer("株式会社みなと商事東京支店", "御中")


def by_customer(invoices: tuple[Invoice, ...]) -> dict[tuple[str, Period], Invoice]:
    return {(each.customer.name, each.period): each for each in invoices}


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_一つの取引先の一つの期間の税抜の明細から一枚の請求書を返す(home: Path) -> None:
    # Given: ガイドの明細行と発行者情報。
    # When
    [invoice] = billing.bill(README_LEDGER_ROWS, AOBA)
    # Then
    assert invoice.number == numbering.number("株式会社みなと商事", NOVEMBER)
    assert set(invoice.totals) == set(README_INVOICE.totals) and len(invoice.totals) == 2
    assert invoice == dataclasses.replace(README_INVOICE, number=invoice.number, totals=invoice.totals)


@supports("test_消費税額は税率ごとに一度だけ切り捨てて載る")
@pytest.mark.parametrize(
    ("prices", "rate", "base", "tax"),
    [
        ((1111, 1111, 1111), 8, 3333, 266),
        ((1234,), 10, 1234, 123),
        ((1,), 10, 1, 0),
        ((10,), 10, 10, 1),
    ],
)
def test_税抜の消費税額は税率ごとの対象額から一度だけ切り捨てる(
    home: Path, prices: tuple[int, ...], rate: int, base: int, tax: int
) -> None:
    # Given: 一つの税率の、一行かいくつかの行。
    rows = [row(2 + i, date(2026, 11, 2 + i), "品目", 1, "箱", price, rate) for i, price in enumerate(prices)]  # type: ignore[arg-type]
    # When
    [invoice] = billing.bill(rows, AOBA)
    # Then
    assert invoice.totals == (RateTotal(rate=rate, base=base, tax=tax),)  # type: ignore[arg-type]
    assert invoice.amount == base + tax
    assert [line.amount for line in invoice.lines] == list(prices)


@supports("test_税込の単価の明細では税込の合計から消費税額が出る")
def test_税込の明細は税率ごとの税込の対象額から消費税額を出し対象額の和を請求する(home: Path) -> None:
    # Given: 単価が税込の明細行。
    rows = (
        row(2, date(2026, 11, 5), "コピー用紙 A4 500枚", 3, "箱", 1100, 10, True),
        row(3, date(2026, 11, 12), "ドリップコーヒー 100袋入", 1, "箱", 1080, 8, True),
        row(4, date(2026, 11, 20), "ボールペン 黒 10本入", 1, "箱", 1000, 10, True),
    )
    # When
    [invoice] = billing.bill(rows, AOBA)
    # Then
    assert invoice.tax_included is True
    assert set(invoice.totals) == {RateTotal(10, 4300, 390), RateTotal(8, 1080, 80)}
    assert len(invoice.totals) == 2
    assert invoice.amount == 5380
    assert [line.amount for line in invoice.lines] == [3300, 1080, 1000]


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
def test_取引先と締めの期間の組ごとに一枚ずつ取引日の順の行で返す(home: Path) -> None:
    # Given: 20日締めの発行者と、名前の似た取引先を含む三つの取引先の、締め日の前後の行。
    issuer = dataclasses.replace(AOBA, payment_terms=PaymentTerms(20, 1, 10))
    rows = (
        row(2, date(2026, 11, 21), "ボールペン 黒 10本入", 5, "箱", 1200, 10),
        row(3, date(2026, 11, 20), "コピー用紙 A4 500枚", 10, "箱", 2800, 10),
        row(4, date(2026, 11, 5), "トナーカートリッジ 黒", 2, "本", 12800, 10, customer=HIKARI),
        row(5, date(2026, 11, 1), "クリアファイル A4 100枚入", 4, "箱", 1350, 10),
        row(6, date(2026, 11, 6), "付箋 75mm 10冊入", 7, "箱", 640, 10, customer=MINATO_TOKYO),
    )
    first, second = Period(date(2026, 10, 21), date(2026, 11, 20)), Period(date(2026, 11, 21), date(2026, 12, 20))
    # When
    invoices = by_customer(billing.bill(rows, issuer))
    # Then
    assert {key: [line.row.line for line in each.lines] for key, each in invoices.items()} == {
        ("株式会社みなと商事", first): [5, 3],
        ("株式会社みなと商事", second): [2],
        ("株式会社ひかり設計", first): [4],
        ("株式会社みなと商事東京支店", first): [6],
    }
    assert {key: (each.issue_date, each.due_date) for key, each in invoices.items()} == {
        ("株式会社みなと商事", first): (date(2026, 11, 20), date(2026, 12, 10)),
        ("株式会社みなと商事", second): (date(2026, 12, 20), date(2027, 1, 10)),
        ("株式会社ひかり設計", first): (date(2026, 11, 20), date(2026, 12, 10)),
        ("株式会社みなと商事東京支店", first): (date(2026, 11, 20), date(2026, 12, 10)),
    }
    assert {key: each.amount for key, each in invoices.items()} == {
        ("株式会社みなと商事", first): 36740,
        ("株式会社みなと商事", second): 6600,
        ("株式会社ひかり設計", first): 28160,
        ("株式会社みなと商事東京支店", first): 4928,
    }
    assert len({each.number for each in invoices.values()}) == 4
    assert all(each.issuer == issuer for each in invoices.values())


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_同じ明細行を二度請求書にさせると同じ請求書を返す(home: Path) -> None:
    # Given: 一度請求書にさせた明細行。
    first = billing.bill(README_LEDGER_ROWS, AOBA)
    # When
    second = billing.bill(README_LEDGER_ROWS, AOBA)
    # Then
    assert second == first


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行記録が壊れていれば番号の採番の断りをそのまま上げる(home: Path) -> None:
    # Given: 発行記録が壊れた状態。
    billing.bill(README_LEDGER_ROWS, AOBA)
    for each in files(place.folder()):
        each.write_bytes(b"\x00broken")
    # When
    with pytest.raises(place.StoreRefused) as refused:
        billing.bill(README_LEDGER_ROWS, AOBA)
    # Then
    assert refused.value.fix.problem == "broken"


@supports("test_画面と紙面の金額は請求の計算が決めた額と同じ")
def test_明細の行の金額は数量と単価の積(home: Path) -> None:
    # Given: 数量の大きな行。
    rows = (row(2, date(2026, 11, 5), "コピー用紙 A4 500枚", 9999, "箱", 999999, 10),)
    # When
    [invoice] = billing.bill(rows, AOBA)
    # Then
    assert invoice.lines == (InvoiceLine(rows[0], 9999 * 999999),)
    assert invoice.totals == (RateTotal(10, 9999 * 999999, 9999 * 999999 // 10),)
    assert invoice.amount == 9999 * 999999 + 9999 * 999999 // 10
    assert invoice.customer == MINATO


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
def test_請求書は最も早い取引日の順に並び税率ごとの合計は10パーセントを先に並ぶ(home: Path) -> None:
    # Given: 軽減税率の行が先に出る、二つの取引先の明細行。
    rows = (
        row(2, date(2026, 11, 12), "ドリップコーヒー 100袋入", 3, "箱", 4500, 8),
        row(3, date(2026, 11, 3), "トナーカートリッジ 黒", 2, "本", 12800, 10, customer=HIKARI),
        row(4, date(2026, 11, 20), "ボールペン 黒 10本入", 5, "箱", 1200, 10),
    )
    # When
    invoices = billing.bill(rows, AOBA)
    # Then: ひかり設計が先で番号も先、みなと商事の合計は 10% が先。
    assert [(each.customer, each.number) for each in invoices] == [(HIKARI, "2026-11-001"), (MINATO, "2026-11-002")]
    assert invoices[1].totals == (RateTotal(10, 6000, 600), RateTotal(8, 13500, 1080))
