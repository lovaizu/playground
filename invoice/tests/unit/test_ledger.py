"""明細の読み取り (ledger.read) の単体ケース。"""

from __future__ import annotations

import dataclasses
import datetime
import os
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import pytest

from invoice import ledger as ledger_module
from invoice.ledger import Customer, LedgerFix, LedgerRefused
from tests.given import COLUMNS, HEADER, HIKARI, INCLUDED_HEADER, README_LEDGER_ROWS, README_ROWS, csv, row

supports = pytest.mark.supports


def refused(path: Path) -> tuple[LedgerFix, ...]:
    """明細を読ませたときの、すべての直すところ。"""
    with pytest.raises(LedgerRefused) as caught:
        ledger_module.read(path)
    return caught.value.fixes


def with_cell(column: str, value: str) -> str:
    """ガイドの一行目の、一つの列だけを替えた行。"""
    cells = README_ROWS[0].split(",")
    cells[COLUMNS.index(column)] = value
    return ",".join(cells)


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("bom", ["", "﻿"])
def test_表計算ソフトが書き出した税抜の明細はすべての行をファイルの順に明細行にする(
    ledger: Callable[..., Path], newline: str, bom: str
) -> None:
    # Given: LibreOffice Calc か Excel が書き出した、ガイドの明細。
    path = ledger(bom + csv(*README_ROWS, newline=newline))
    # When
    rows = ledger_module.read(path)
    # Then
    assert rows == README_LEDGER_ROWS


@supports("test_税込の単価の明細では税込の合計から消費税額が出る")
def test_税込の見出しの明細は単価を税込として読む(ledger: Callable[..., Path]) -> None:
    # Given
    path = ledger(csv(README_ROWS[0], header=INCLUDED_HEADER))
    # When
    rows = ledger_module.read(path)
    # Then
    assert rows == (row(2, datetime.date(2026, 11, 5), "コピー用紙 A4 500枚", 10, "箱", 2800, 10, True),)


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
def test_取引日の順でない行もファイルの順のまま読み取引先ごとの名称と敬称を読む(ledger: Callable[..., Path]) -> None:
    # Given: 取引日が前後し、二つの取引先と単位の空の行がある明細。
    path = ledger(
        csv(
            "株式会社ひかり設計,2026-11-27,付箋 75mm 10冊入,7,,640,10%",
            README_ROWS[0],
        ),
    )
    # When
    rows = ledger_module.read(path)
    # Then
    assert rows == (
        row(2, datetime.date(2026, 11, 27), "付箋 75mm 10冊入", 7, "", 640, 10, customer=HIKARI),
        row(3, datetime.date(2026, 11, 5), "コピー用紙 A4 500枚", 10, "箱", 2800, 10),
    )


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_見出しだけの明細は行がないことと一行の例を返す(ledger: Callable[..., Path]) -> None:
    # Given
    path = ledger(csv())
    # When
    [fix] = refused(path)
    # Then
    assert (fix.path, fix.problem, fix.line, fix.column, fix.given, fix.detail) == (
        path,
        "no_rows",
        None,
        None,
        None,
        "",
    )
    assert len(ledger_module.read(ledger(csv(fix.expected)))) == 1


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_ないパスはその直すところ一つだけを返す(tmp_path: Path) -> None:
    # Given
    path = tmp_path / "2026年11月分明細.csv"
    # When
    [fix] = refused(path)
    # Then
    assert (fix.path, fix.problem, fix.line, fix.column, fix.given, fix.expected) == (
        path,
        "not_found",
        None,
        None,
        None,
        "",
    )


@supports("test_明細の直すところをすべて示し何も印刷しない")
@pytest.mark.parametrize("kind", ["folder", "shift_jis", "no_permission"])
def test_読めないファイルはその直すところ一つだけを返す(tmp_path: Path, ledger: Callable[..., Path], kind: str) -> None:
    # Given: フォルダー、Shift_JIS で保存した明細、または読む権限のない明細。
    if kind == "folder":
        path = tmp_path / "明細"
        path.mkdir()
    elif kind == "shift_jis":
        path = ledger(csv(*README_ROWS), encoding="shift_jis")
    else:
        if os.geteuid() == 0:
            pytest.skip("root はどのファイルも読める")
        path = ledger(csv(*README_ROWS))
        path.chmod(0)
    # When
    [fix] = refused(path)
    # Then
    assert (fix.path, fix.problem, fix.line, fix.column, fix.given, fix.expected) == (
        path,
        "unreadable",
        None,
        None,
        None,
        "",
    )


@supports("test_明細の直すところをすべて示し何も印刷しない")
@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("取引先", ""),
        ("取引日", "2026-11-31"),
        ("取引日", "2026/11/31"),
        ("取引日", ""),
        ("取引日", "2026/11/5"),
        ("取引日", "2026-11/05"),
        ("取引日", "11/05"),
        ("数量", "十"),
        ("数量", ""),
        ("数量", "0"),
        ("数量", "-1"),
        ("数量", "1.5"),
        ("単価(税抜)", "二千八百"),
        ("単価(税抜)", ""),
        ("単価(税抜)", "0"),
        ("税率", "5%"),
        ("税率", ""),
        ("税率", "10"),
    ],
)
def test_受け付けない値の行はその行と列と値と受け付ける例を返す(
    ledger: Callable[..., Path], column: str, value: str
) -> None:
    # Given
    path = ledger(csv(with_cell(column, value)))
    # When
    [fix] = refused(path)
    # Then
    assert (fix.path, fix.problem, fix.line, fix.column, fix.given) == (path, "bad_value", 2, column, value or None)
    assert len(ledger_module.read(ledger(csv(with_cell(column, fix.expected))))) == 1


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_誤りのある行がいくつあってもすべての行を読み終えてすべての直すところを返す(
    ledger: Callable[..., Path],
) -> None:
    # Given: 一行目と三行目に誤りがあり、三行目には二つの誤りがある明細。
    path = ledger(
        csv(
            with_cell("取引日", "2026-11-31"),
            README_ROWS[1],
            "株式会社みなと商事,2026-11-20,ボールペン 黒 10本入,五,箱,1200,5%",
        ),
    )
    # When
    fixes = refused(path)
    # Then
    assert sorted((fix.problem, fix.line, fix.column, fix.given) for fix in fixes) == [
        ("bad_value", 2, "取引日", "2026-11-31"),
        ("bad_value", 4, "数量", "五"),
        ("bad_value", 4, "税率", "5%"),
    ]


@supports("test_明細の直すところをすべて示し何も印刷しない")
@pytest.mark.parametrize(
    ("header", "column", "given"),
    [
        ("取引先,取引日,品目,数量,単位,単価,税率", "単価", "単価"),
        ("取引先,取引日,品目,数量,単位,単価(税別),税率", "単価(税別)", "単価(税別)"),
        ("取引先,取引日,品目,数量,単位,単価(税抜)", "税率", None),
    ],
)
def test_受け付けない見出しは見出しの行の直すところを返す(
    ledger: Callable[..., Path], header: str, column: str, given: str | None
) -> None:
    # Given: 単価が税抜か税込かを示さない見出し、税抜とも税込とも書かない見出し、または税率の列のない見出し。
    rows = [",".join(each.split(",")[: header.count(",") + 1]) for each in README_ROWS]
    path = ledger(csv(*rows, header=header))
    # When
    fixes = refused(path)
    # Then
    assert [(fix.problem, fix.line, fix.column, fix.given) for fix in fixes if fix.line == 1] == [
        ("bad_value", 1, column, given)
    ]


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_見出しに誤りがあり行もない明細は両方の直すところを返す(ledger: Callable[..., Path]) -> None:
    # Given
    path = ledger(csv(header="取引先,取引日,品目,数量,単位,単価,税率"))
    # When
    fixes = refused(path)
    # Then
    assert sorted((fix.problem, fix.line) for fix in fixes) == [("bad_value", 1), ("no_rows", None)]


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_明細のファイルを書き換えない(ledger: Callable[..., Path]) -> None:
    # Given
    path = ledger(csv(*README_ROWS))
    before = path.read_bytes()
    # When
    ledger_module.read(path)
    # Then
    assert path.read_bytes() == before
    assert HEADER in before.decode("utf-8")


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_取引日は年と月と日をスラッシュで区切っても読む(ledger: Callable[..., Path]) -> None:
    # Given: 取引日を 2026/11/05 と書いた明細。
    path = ledger(csv(with_cell("取引日", "2026/11/05")))
    # When
    rows = ledger_module.read(path)
    # Then
    assert rows == (README_LEDGER_ROWS[0],)


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
@pytest.mark.parametrize(("column", "value"), [("数量", "1"), ("単価(税抜)", "1")])
def test_数量と単価は1から受け付ける(ledger: Callable[..., Path], column: str, value: str) -> None:
    # Given: 数量か単価を、受け付ける最も小さい 1 とした明細。
    path = ledger(csv(with_cell(column, value)))
    # When
    [read_row] = ledger_module.read(path)
    # Then
    expected = {"数量": {"quantity": 1}, "単価(税抜)": {"unit_price": 1}}[column]
    assert read_row == dataclasses.replace(README_LEDGER_ROWS[0], **expected)  # type: ignore[arg-type]


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_全角の英数字と記号の明細と見出しは半角に読み替えて読む(ledger: Callable[..., Path]) -> None:
    # Given: 見出しの括弧と、取引日、品目、数量、単価、税率を全角で書いた明細。
    path = ledger(
        csv(
            "株式会社みなと商事,２０２６－１１－０５,コピー用紙 Ａ４ ５００枚,１０,箱,２８００,１０％",
            header="取引先,取引日,品目,数量,単位,単価（税抜）,税率",
        ),
    )
    # When
    rows = ledger_module.read(path)
    # Then
    assert rows == (README_LEDGER_ROWS[0],)


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_半角カナの品目と単位は全角に読み替えて読む(ledger: Callable[..., Path]) -> None:
    # Given: 品目と単位を半角カナで書いた明細。
    path = ledger(csv("株式会社みなと商事,2026-11-12,ﾄﾞﾘｯﾌﾟｺｰﾋｰ 100袋入,3,ｹｰｽ,4500,8%"))
    # When
    rows = ledger_module.read(path)
    # Then
    assert rows == (row(2, datetime.date(2026, 11, 12), "ドリップコーヒー 100袋入", 3, "ケース", 4500, 8),)


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
@pytest.mark.parametrize(
    ("name", "honorific"),
    [
        ("株式会社みなと商事", "御中"),
        ("みなと商事株式会社", "御中"),
        ("合同会社かもめ設計", "御中"),
        ("有限会社やまと食品", "御中"),
        ("一般社団法人あおい会", "御中"),
        ("山田 太郎", "様"),
        ("山田太郎", "様"),
        ("みなと商事", "様"),
    ],
)
def test_取引先の名称に法人格があれば御中なければ様と読む(
    ledger: Callable[..., Path], name: str, honorific: Literal["御中", "様"]
) -> None:
    # Given: 法人格のある名称か、ない名称の取引先の明細。
    path = ledger(csv(with_cell("取引先", name)))
    # When
    [read_row] = ledger_module.read(path)
    # Then
    assert read_row.customer == Customer(name=name, honorific=honorific)
