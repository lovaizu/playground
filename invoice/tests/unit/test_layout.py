"""請求書の組版 (layout.typeset) の単体ケース。"""

from __future__ import annotations

import dataclasses
import io
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

from invoice import layout
from invoice.billing import Invoice, InvoiceLine, RateTotal
from invoice.ledger import Customer
from tests.given import HIKARI, README_INVOICE, README_LINES, README_SHEETS, README_TOTALS, pages, paper, row, sheets

supports = pytest.mark.supports


def replaced(**changes: object) -> Invoice:
    return dataclasses.replace(README_INVOICE, **changes)  # type: ignore[arg-type]


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_一枚の請求書からガイドのとおりの紙面を一つ返す(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Given: ノートPCの書体を読めない状態と、ガイドの請求書。
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("FONTCONFIG_FILE", str(tmp_path / "empty.conf"))
    (tmp_path / "empty.conf").write_text("<fontconfig></fontconfig>", encoding="utf-8")
    # When
    [document] = layout.typeset([README_INVOICE])
    # Then
    assert document.pdf.startswith(b"%PDF")
    assert document.sheets == pages(document) == 1
    assert paper(document) in README_SHEETS
    assert all(embedded(font) for font in fonts(document))


def fonts(document: layout.PrintDocument) -> list[Any]:
    """紙面の各ページが使う書体。"""
    found: list[Any] = []
    for page in PdfReader(io.BytesIO(document.pdf)).pages:
        resources: Any = page["/Resources"]
        found += [each.get_object() for each in resources.get_object()["/Font"].get_object().values()]
    return found


def embedded(font: Any) -> bool:
    """書体が、その字形を PDF の中に持つか。"""
    parts = [font, *[each.get_object() for each in font.get("/DescendantFonts", [])]]
    return any(
        key in part["/FontDescriptor"].get_object()
        for part in parts
        if "/FontDescriptor" in part
        for key in ("/FontFile", "/FontFile2", "/FontFile3")
    )


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_請求書がなければ紙面を返さない() -> None:
    # Given
    # When
    documents = layout.typeset([])
    # Then
    assert documents == ()


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
def test_いくつかの請求書から受け取った順に紙面を一つずつ返す() -> None:
    # Given: 宛先と番号の違う三枚の請求書。
    invoices = [
        replaced(customer=HIKARI, number="A-1"),
        README_INVOICE,
        replaced(customer=Customer("山田 太郎", "様"), number="A-3"),
    ]
    # When
    documents = layout.typeset(invoices)
    # Then
    assert len(documents) == 3
    for document, name, number in zip(
        documents,
        ("株式会社ひかり設計 御中", "株式会社みなと商事 御中", "山田 太郎 様"),
        ("A-1", "2026-11-001", "A-3"),
        strict=True,
    ):
        assert paper(document) in sheets(
            name, number, "2026年11月30日", "51,980", "2026年12月31日", README_LINES, README_TOTALS
        ), f"{name} の紙面"


@supports("test_税込の単価の明細では税込の合計から消費税額が出る")
def test_税込の請求書は単価と金額と対象額を税込と示す() -> None:
    # Given
    invoice = replaced(tax_included=True)
    # When
    [document] = layout.typeset([invoice])
    # Then
    assert paper(document) in sheets(
        "株式会社みなと商事 御中",
        "2026-11-001",
        "2026年11月30日",
        "51,980",
        "2026年12月31日",
        README_LINES,
        README_TOTALS,
        basis="税込",
    )


@supports("test_画面と紙面の金額は請求の計算が決めた額と同じ")
def test_額は請求書のものをそのまま載せ計算し直さない() -> None:
    # Given: 明細と合わない額を持つ請求書。
    invoice = replaced(amount=99999, totals=(RateTotal(10, 1, 2), RateTotal(8, 3, 4)))
    # When
    [document] = layout.typeset([invoice])
    # Then
    assert paper(document) in sheets(
        "株式会社みなと商事 御中",
        "2026-11-001",
        "2026年11月30日",
        "99,999",
        "2026年12月31日",
        README_LINES,
        ("10% 1 2", "8%(軽減税率) 3 4"),
    )


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_単位の空の行は数量だけを載せる() -> None:
    # Given
    line = InvoiceLine(row(2, date(2026, 11, 5), "コピー用紙 A4 500枚", 10, "", 2800, 10), 28000)
    invoice = replaced(lines=(line,))
    # When
    [document] = layout.typeset([invoice])
    # Then
    assert paper(document) in sheets(
        "株式会社みなと商事 御中",
        "2026-11-001",
        "2026年11月30日",
        "51,980",
        "2026年12月31日",
        ("2026年11月5日 コピー用紙 A4 500枚 10 2,800 10% 28,000",),
        README_TOTALS,
    )


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
@pytest.mark.parametrize("count", [1, 80])
def test_用紙の枚数は紙面のページの数ですべての行を載せる(count: int) -> None:
    # Given: 一行か、八十行の明細の請求書。
    lines = tuple(
        InvoiceLine(row(2 + i, date(2026, 11, 1 + i % 30), f"品目 {i:03}", 1, "個", 100, 10), 100) for i in range(count)
    )
    invoice = replaced(lines=lines)
    # When
    [document] = layout.typeset([invoice])
    # Then
    assert document.sheets == pages(document) >= 1
    text = paper(document)
    places = [text.find(f"{day}日 品目 {i:03} 1 個 100 10% 100") for i, day in ((i, 1 + i % 30) for i in range(count))]
    assert -1 not in places, "すべての行が載る"
    assert places == sorted(places), "行は受け取った順に載る"
