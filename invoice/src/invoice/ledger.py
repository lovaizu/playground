"""明細のファイルを、どの形なら受け付け、各列をどう読んで明細行にするか。"""

from __future__ import annotations

import csv
import datetime
import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from invoice.width import narrowed

TaxRate = Literal[8, 10]
"""明細行の消費税率 (%)。8 は軽減税率で、請求書にその旨を載せる。"""


@dataclass(frozen=True)
class Customer:
    """取引先: 請求書の宛先。"""

    name: str
    """取引先の正式な名称。明細の「取引先」の列を、全角の英数字と記号を半角に読み替えたもの。"""
    honorific: Literal["御中", "様"]
    """宛名の敬称。名称に株式会社や合同会社などの法人格があれば「御中」、なければ「様」。
    例: `株式会社青葉商事` は「御中」、`山田太郎` は「様」。
    明細の「取引先」の列の名称から、このモジュールが読み取る。"""


@dataclass(frozen=True)
class LedgerRow:
    """明細行: 一つの取引を表し、請求書の明細の一行になる。"""

    line: int
    """明細のファイルでの行の番号。見出しの行を 1 として数える。"""
    customer: Customer
    """取引先。"""
    date: datetime.date
    """取引日。"""
    description: str
    """品目。明細の「品目」の列。"""
    quantity: int
    """数量。正の整数。"""
    unit: str
    """単位。明細の「単位」の列。例: `箱`。空なら数量だけを載せる。"""
    unit_price: int
    """単価。円の正の整数。"""
    tax_rate: TaxRate
    """消費税率。"""
    tax_included: bool
    """単価が税込なら True (P3.3)。"""


LedgerProblem: TypeAlias = Literal["not_found", "unreadable", "no_rows", "bad_value"]
"""明細を請求書にできないわけの種類。

not_found: 渡されたパスに、ファイルがない。
unreadable: ファイルはあるが、読めない。読む権限がない、フォルダーである、
    または UTF-8 の CSV として読めないとき。
no_rows: 見出しの行のほかに、明細の行が一つもない。
bad_value: 明細の行か見出しの列に、受け付けない値がある。
"""


@dataclass(frozen=True)
class LedgerFix:
    """直すところ: 明細を請求書にできない一つのわけと、受け付ける形の例。

    コマンドはこの値だけから、どのファイルの、どの行の何をどう直すかを、
    problem ごとに日本語で示す (P1.2)。
    """

    path: Path
    """渡された明細のファイルのパス。"""
    problem: LedgerProblem
    """わけの種類。"""
    line: int | None
    """誤りの行の番号。見出しの行は 1。problem が bad_value でなければ None。"""
    column: str | None
    """誤りの列の見出し。見出しの誤りでは、書かれていた見出しか、欠けた列の見出し。
    problem が bad_value でなければ None。"""
    given: str | None
    """明細に書かれていた値。値がない、または problem が bad_value でなければ None。"""
    expected: str
    """受け付ける形の例。そのまま書けば受け付ける。bad_value では値の例。例: `2026-11-20`。
    no_rows では明細の一行の例。not_found と unreadable では空。"""
    rule: str
    """bad_value で、受け付ける形の決まりを、利用者の言葉で。ほかでは空。
    例: `取引日は 2026-11-20 か 2026/11/20 の形の、ある日付で書きます。`。"""
    detail: str
    """ファイルシステムが返したわけか、UTF-8 として読めない場所。なければ空。"""


class LedgerRefused(Exception):
    """明細を請求書にできないときに上がり、すべての直すところを持つ。"""

    def __init__(self, fixes: tuple[LedgerFix, ...]) -> None:
        super().__init__(fixes)
        self.fixes = fixes


_EXCLUDED, _INCLUDED = "単価(税抜)", "単価(税込)"
_COLUMNS = ("取引先", "取引日", "品目", "数量", "単位", _EXCLUDED, "税率")
"""明細の見出しの列を、その順に。単価の列は、税込なら `単価(税込)`。"""

_EXAMPLE_ROW = "株式会社みなと商事,2026-11-05,コピー用紙 A4 500枚,10,箱,2800,10%"
"""明細の一行の例。"""

_CORPORATE = (
    "株式会社",
    "有限会社",
    "合同会社",
    "合名会社",
    "合資会社",
    "相互会社",
    "法人",
    "組合",
)
"""取引先の名称にあれば、法人とみなす法人格。略した書き方は含めない。"""


class _Bad(Exception):
    """一つの列の値を受け付けないときに、その列を読む関数が上げる。"""

    def __init__(self, expected: str, rule: str) -> None:
        super().__init__(expected, rule)
        self.expected = expected
        self.rule = rule


def read(path: Path) -> tuple[LedgerRow, ...]:
    """明細を読ませる (S1, S3, S4)。

    受け取る: 明細のファイルのパス。UTF-8 の CSV で、先頭の BOM はあってもよい。
        見出しは、取引先、取引日、品目、数量、単位、`単価(税抜)` か `単価(税込)`、税率の
        七つの列をこの順に。見出しとそれぞれの値は、全角の数字・英字・記号を半角に、
        半角カナを全角に読み替えてから確かめる。
        取引日は YYYY-MM-DD か YYYY/MM/DD、数量と単価は正の整数、税率は 10% か 8%。
        取引先は空でない文字列。品目と単位は、空でもそのまま読む。
    返す: 明細のすべての行を、ファイルの順に明細行として。一行以上。
        取引先の名称からは、宛名の敬称も読み取る。
    ほかに変えるもの: なし。明細のファイルを読むだけで、書かない。
    断るとき:
        LedgerRefused: 明細を請求書にできないとき。直すところの problem で、
            どのわけかを分ける。
            not_found: パスにファイルがないとき。その直すところ一つだけを持って上がる。
            unreadable: ファイルを読めないとき。その直すところ一つだけを持って上がる。
            no_rows: 見出しのほかに行が一つもないとき。見出しに bad_value が
                あれば、それらとともに持って上がる。
            bad_value: 一行でも請求書にできない行か、受け付けない見出しがあるとき。
                すべての行を読み終えてから、すべての直すところを、行の順、列の順に持って上がる (P1.3)。
    """
    records = _records(path)
    header = [narrowed(cell) for cell in records[0][1]] if records else []
    fixes = _header_fixes(path, header)
    tax_included = len(header) > 5 and header[5] == _INCLUDED
    rows: list[LedgerRow] = []
    for number, record in records[1:]:
        row = _row(path, number, record, tax_included, fixes)
        if row is not None:
            rows.append(row)
    if len(records) < 2:
        fixes.append(LedgerFix(path, "no_rows", None, None, None, _EXAMPLE_ROW, "", ""))
    if fixes:
        raise LedgerRefused(tuple(fixes))
    return tuple(rows)


def _records(path: Path) -> list[tuple[int, list[str]]]:
    """明細のファイルの各行を、見出しを 1 とした行の番号と、列の値の並びとして。"""
    try:
        data = path.read_bytes()
    except FileNotFoundError as error:
        raise _refused(path, "not_found", error.strerror) from error
    except OSError as error:
        raise _refused(path, "unreadable", error.strerror) from error
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise _refused(
            path, "unreadable", f"先頭から {error.start + 1} バイト目が、UTF-8 の字ではありません"
        ) from error
    records = list(csv.reader(io.StringIO(text, newline="")))
    return list(enumerate(records, start=1))


def _refused(path: Path, problem: LedgerProblem, detail: str | None) -> LedgerRefused:
    return LedgerRefused((LedgerFix(path, problem, None, None, None, "", "", detail or ""),))


def _header_fixes(path: Path, header: list[str]) -> list[LedgerFix]:
    """見出しの行の、受け付けない列の直すところ。"""
    fixes = []
    for at, expected in enumerate(_COLUMNS):
        given = header[at] if at < len(header) else None
        accepted = (_EXCLUDED, _INCLUDED) if expected == _EXCLUDED else (expected,)
        if given not in accepted:
            rule = f"{at + 1} 列目の見出しは「{'」か「'.join(accepted)}」と書きます。"
            fixes.append(LedgerFix(path, "bad_value", 1, given or expected, given or None, expected, rule, ""))
    return fixes


def _row(path: Path, number: int, record: list[str], tax_included: bool, fixes: list[LedgerFix]) -> LedgerRow | None:
    """明細の一行を明細行に読む。受け付けない値があれば、その直すところを fixes に足して None。"""
    cells = [narrowed(cell) for cell in record] + [""] * (len(_COLUMNS) - len(record))
    values: list[object] = []
    for at, column in enumerate(_COLUMNS):
        name = _INCLUDED if column == _EXCLUDED and tax_included else column
        try:
            values.append(_READERS[column](cells[at]))
        except _Bad as bad:
            fixes.append(LedgerFix(path, "bad_value", number, name, cells[at] or None, bad.expected, bad.rule, ""))
    if len(values) < len(_COLUMNS):
        return None
    customer, day, description, quantity, unit, price, rate = values
    return LedgerRow(
        line=number,
        customer=customer,  # type: ignore[arg-type]
        date=day,  # type: ignore[arg-type]
        description=description,  # type: ignore[arg-type]
        quantity=quantity,  # type: ignore[arg-type]
        unit=unit,  # type: ignore[arg-type]
        unit_price=price,  # type: ignore[arg-type]
        tax_rate=rate,  # type: ignore[arg-type]
        tax_included=tax_included,
    )


def _customer(cell: str) -> Customer:
    if cell == "":
        raise _Bad("株式会社みなと商事", "取引先は、請求書の宛先にする正式な名称で書きます。")
    corporate = any(form in cell for form in _CORPORATE)
    return Customer(cell, "御中" if corporate else "様")


def _date(cell: str) -> datetime.date:
    bad = _Bad("2026-11-20", "取引日は 2026-11-20 か 2026/11/20 の形の、ある日付で書きます。")
    found = re.fullmatch(r"([0-9]{4})([-/])([0-9]{2})\2([0-9]{2})", cell)
    if found is None:
        raise bad
    try:
        return datetime.date(int(found[1]), int(found[3]), int(found[4]))
    except ValueError as error:
        raise bad from error


def _text(cell: str) -> str:
    return cell


def _positive(example: str, rule: str) -> Callable[[str], int]:
    def read_positive(cell: str) -> int:
        if re.fullmatch(r"[0-9]+", cell) is None or int(cell) == 0:
            raise _Bad(example, rule)
        return int(cell)

    return read_positive


def _rate(cell: str) -> TaxRate:
    rates: dict[str, TaxRate] = {"10%": 10, "8%": 8}
    if cell not in rates:
        raise _Bad("10%", "税率は 10% か、軽減税率の品目なら 8% と書きます。")
    return rates[cell]


_READERS: dict[str, Callable[[str], object]] = {
    "取引先": _customer,
    "取引日": _date,
    "品目": _text,
    "数量": _positive("10", "数量は、1 以上の整数で書きます。"),
    "単位": _text,
    _EXCLUDED: _positive("2800", "単価は、円の 1 以上の整数で、カンマを付けずに書きます。"),
    "税率": _rate,
}
"""列ごとに、その列の値を読む関数。受け付けない値には _Bad を上げる。"""
