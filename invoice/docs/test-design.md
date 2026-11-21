# `invoice` のテストケース

## エンドツーエンドのケース

E2E ケースは、ガイドの「使ってみる」のとおりに、一か月分の明細で invoice を通しで動かす。

既定のプリンターだけは、`printing.send` を代役に替える。

ケースは、ここに挙げるテストのコードだけで述べる。

`invoice/tests/__init__.py`、`invoice/tests/unit/__init__.py`、`invoice/tests/integration/__init__.py`、`invoice/tests/e2e/__init__.py` は、中身のない空のファイルとする。

`invoice/tests/given.py` は、各段のケースが共に使う値と代役を置く。

```python
"""invoice のケースが共に使う、ガイドの「使ってみる」の値と、端末とプリンターの代役。"""

from __future__ import annotations

import datetime
import io
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from invoice import issuer, layout, printing
from invoice.billing import Invoice, InvoiceLine, RateTotal
from invoice.issuer import BankAccount, Issuer, IssuerItem, PaymentTerms
from invoice.ledger import Customer, LedgerRow, TaxRate
from invoice.periods import Period

COLUMNS = ("取引先", "取引日", "品目", "数量", "単位", "単価(税抜)", "税率")
"""税抜の明細の見出しの列。"""

HEADER = ",".join(COLUMNS)
"""税抜の明細の見出しの行。"""

INCLUDED_HEADER = "取引先,取引日,品目,数量,単位,単価(税込),税率"
"""税込の明細の見出しの行。"""

README_ROWS = (
    "株式会社みなと商事,2026-11-05,コピー用紙 A4 500枚,10,箱,2800,10%",
    "株式会社みなと商事,2026-11-12,ドリップコーヒー 100袋入,3,箱,4500,8%",
    "株式会社みなと商事,2026-11-20,ボールペン 黒 10本入,5,箱,1200,10%",
)
"""ガイドの「使ってみる」の、11 月分の明細の行。"""


def csv(*rows: str, header: str = HEADER, newline: str = "\n") -> str:
    """見出しと行を、表計算ソフトが CSV で書き出すとおり一行ずつ並べた明細の中身。"""
    return "".join(f"{line}{newline}" for line in (header, *rows))


ITEMS: tuple[IssuerItem, ...] = (
    "name",
    "registration_number",
    "payment_terms",
    "bank_name",
    "bank_branch",
    "account_type",
    "account_number",
    "account_holder",
)
"""発行者情報の事柄を、初回に尋ねられる順に。"""

AOBA_ANSWERS = (
    "株式会社あおば事務用品",
    "T1234567890123",
    "月末締め翌月末払い",
    "さくら銀行",
    "本店営業部",
    "普通",
    "1234567",
    "カ)アオバジムヨウヒン",
)
"""ガイドの「使ってみる」で、初回に利用者が答える発行者の情報を、尋ねられる順に。"""

AOBA_LABELS = (
    "発行者の正式名称",
    "登録番号(T と 13 桁の数字)",
    "締め日と支払条件(例: 月末締め翌月末払い)",
    "お振込先の銀行名",
    "支店名",
    "口座種別(普通か当座)",
    "口座番号",
    "口座名義(カナ)",
)
"""ガイドの「使ってみる」で、初回に利用者が尋ねられる事柄の名前を、尋ねられる順に。"""

AOBA = Issuer(
    name="株式会社あおば事務用品",
    registration_number="T1234567890123",
    payment_terms=PaymentTerms(closing_day="month_end", month=1, payment_day="month_end"),
    bank=BankAccount(
        name="さくら銀行",
        branch="本店営業部",
        account_type="普通",
        account_number="1234567",
        account_holder="カ)アオバジムヨウヒン",
    ),
)
"""ガイドの答えから残る、株式会社あおば事務用品の発行者情報。"""

MINATO = Customer(name="株式会社みなと商事", honorific="御中")
"""ガイドの「使ってみる」の取引先。"""

MINATO_TOKYO = Customer(name="株式会社みなと商事東京支店", honorific="御中")
"""MINATO と名前の似た、別の取引先。"""

HIKARI = Customer(name="株式会社ひかり設計", honorific="御中")
"""あおば事務用品の、もう一つの取引先。"""

NOVEMBER = Period(start=datetime.date(2026, 11, 1), end=datetime.date(2026, 11, 30))
"""月末締めの、2026 年 11 月の締めの期間。"""


def row(
    line: int,
    day: datetime.date,
    description: str,
    quantity: int,
    unit: str,
    unit_price: int,
    tax_rate: TaxRate,
    tax_included: bool = False,
    customer: Customer = MINATO,
) -> LedgerRow:
    """明細の一行を、明細行として。"""
    return LedgerRow(
        line=line,
        customer=customer,
        date=day,
        description=description,
        quantity=quantity,
        unit=unit,
        unit_price=unit_price,
        tax_rate=tax_rate,
        tax_included=tax_included,
    )


README_LEDGER_ROWS = (
    row(2, datetime.date(2026, 11, 5), "コピー用紙 A4 500枚", 10, "箱", 2800, 10),
    row(3, datetime.date(2026, 11, 12), "ドリップコーヒー 100袋入", 3, "箱", 4500, 8),
    row(4, datetime.date(2026, 11, 20), "ボールペン 黒 10本入", 5, "箱", 1200, 10),
)
"""ガイドの明細を読んだ明細行。"""

README_INVOICE = Invoice(
    number="2026-11-001",
    customer=MINATO,
    period=NOVEMBER,
    issue_date=datetime.date(2026, 11, 30),
    due_date=datetime.date(2026, 12, 31),
    issuer=AOBA,
    tax_included=False,
    lines=tuple(
        InvoiceLine(row=each, amount=amount)
        for each, amount in zip(README_LEDGER_ROWS, (28000, 13500, 6000), strict=True)
    ),
    totals=(RateTotal(rate=10, base=34000, tax=3400), RateTotal(rate=8, base=13500, tax=1080)),
    amount=51980,
)
"""ガイドの「使ってみる」で印刷される請求書。"""

README_PAPER = (
    "請求書",
    "株式会社みなと商事 御中",
    "株式会社あおば事務用品",
    "登録番号: T1234567890123",
    "請求書番号: 2026-11-001",
    "発行日: 2026年11月30日",
    "ご請求金額(税込): 51,980 円",
    "お支払期限: 2026年12月31日",
    "お振込先: さくら銀行 本店営業部 普通 1234567 カ)アオバジムヨウヒン",
    "取引日 品目 数量 単価(税抜) 税率 金額(税抜)",
    "2026年11月5日 コピー用紙 A4 500枚 10 箱 2,800 10% 28,000",
    "2026年11月12日 ドリップコーヒー 100袋入 3 箱 4,500 8%(軽減税率) 13,500",
    "2026年11月20日 ボールペン 黒 10本入 5 箱 1,200 10% 6,000",
    "税率 対象額(税抜) 消費税額",
    "10% 34,000 3,400",
    "8%(軽減税率) 13,500 1,080",
    "合計(税込): 51,980 円",
)
"""ガイドの「使ってみる」で、プリンターから出る請求書に載る行を、空白を一つにつめて。

明細の取引日は、layout.typeset の契約のとおり「2026年11月5日」の形で載る。
"""


def checked(**changed: str) -> dict[IssuerItem, issuer.Answer]:
    """ガイドの答えを、changed の事柄だけ替えて確かめさせた、事柄ごとの答え。何も残さない。"""
    answers = dict(zip(ITEMS, AOBA_ANSWERS, strict=True)) | changed
    return {item: issuer.check(item, answers[item]) for item in ITEMS}


def save_aoba(**changed: str) -> Issuer:
    """ガイドの答えを、changed の事柄だけ替えて確かめさせ、発行者情報として残させる。"""
    return issuer.save(checked(**changed))


def paper(document: layout.PrintDocument) -> str:
    """紙面に載る文字を、空白の並びを一つの空白につめ、ページの順につなげたもの。"""
    reader = PdfReader(io.BytesIO(document.pdf))
    return " ".join(" ".join(page.extract_text().split()) for page in reader.pages)


def pages(document: layout.PrintDocument) -> int:
    """紙面の PDF のページの数。"""
    return len(PdfReader(io.BytesIO(document.pdf)).pages)


def asked(out: str) -> list[str]:
    """端末に示された文のうち、尋ねた事柄の名前を、尋ねた順に。"""
    names = "|".join(re.escape(label) for label in sorted(AOBA_LABELS, key=len, reverse=True))
    return re.findall(names, out)


def billed(out: str) -> dict[str, tuple[str, str]]:
    """端末に示された請求書ごとの行を、宛名から請求書番号とご請求金額へ。"""
    found = re.findall(r"^(.+): 請求書番号 (\S+)、ご請求金額 ([0-9,]+) 円$", out, re.M)
    return {name: (number, amount) for name, number, amount in found}


def printed(sheets: int) -> str:
    """ガイドのとおりに、送った既定のプリンターの名前と印刷した枚数を示す行。"""
    return f"既定のプリンター「経理室プリンター」で {sheets} 枚を印刷しました。"


def files(folder: Path) -> dict[Path, bytes]:
    """フォルダーの中のすべてのファイルと、その中身。フォルダーがなければ空。"""
    if not folder.exists():
        return {}
    return {each: each.read_bytes() for each in sorted(folder.rglob("*")) if each.is_file()}


@contextmanager
def fresh_home() -> Iterator[Path]:
    """まっさらなホームフォルダー。プロパティが試す入力ごとに一つ使う。"""
    before = os.environ.get("HOME")
    with tempfile.TemporaryDirectory() as folder:
        os.environ["HOME"] = folder
        try:
            yield Path(folder)
        finally:
            if before is None:
                del os.environ["HOME"]
            else:
                os.environ["HOME"] = before


class Terminal:
    """利用者の端末の入力の代役。答えを順に返し、尽きると利用者が Ctrl+C で止めたことにする。"""

    def __init__(self, answers: tuple[str, ...]) -> None:
        self.answers = list(answers)

    def readline(self) -> str:
        if not self.answers:
            raise KeyboardInterrupt
        return self.answers.pop(0) + "\n"

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        raise io.UnsupportedOperation("fileno")


@dataclass
class Printer:
    """既定のプリンターの代役。printing.send に替わり、受け取った紙面を順に持ち、名前を返す。

    refuse_at を置くと、その数の紙面を受け取ったあとは、problem のわけで断る。
    """

    sent: list[layout.PrintDocument] = field(default_factory=list)
    refuse_at: int | None = None
    problem: str = "send_failed"
    name: str = "経理室プリンター"

    def send(self, document: layout.PrintDocument) -> str:
        if self.refuse_at is not None and len(self.sent) >= self.refuse_at:
            raise printing.PrintRefused(printing.PrintFix(self.problem, "代役が断った"))  # type: ignore[arg-type]
        self.sent.append(document)
        return self.name
```

`invoice/tests/conftest.py` は、ケースが受け取る置き場と代役を渡す。

```python
"""invoice のケースが受け取る、まっさらなホームフォルダー、明細のファイル、端末とプリンターの代役。"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import printing
from invoice.issuer import Issuer
from tests.given import Printer, Terminal, save_aoba


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--host", action="store_true", help="本物の印刷システムを動かすケースも走らせる")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "supports(*names): ケースが確かめる、一つ上の段の要素かケース")
    config.addinivalue_line("markers", "host: 本物の印刷システムを動かすケース。--host のときだけ走る")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--host"):
        return
    for item in items:
        if "host" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="本物の印刷システムを動かすため、--host のときだけ走る"))


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """利用者のまっさらなホームフォルダー。invoice が残すものは、この中に置かれる。"""
    folder = tmp_path / "home"
    folder.mkdir()
    monkeypatch.setenv("HOME", str(folder))
    return folder


@pytest.fixture
def ledger(tmp_path: Path) -> Callable[..., Path]:
    """明細の中身を、利用者が保存するとおりのファイルにして、そのパスを返す。"""

    def write(text: str, name: str = "2026年11月分明細.csv", encoding: str = "utf-8") -> Path:
        path = tmp_path / name
        path.write_bytes(text.encode(encoding))
        return path

    return write


@pytest.fixture
def terminal(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Terminal]:
    """利用者が端末で打つ答えを、順に渡す代役を置く。"""

    def answering(*answers: str) -> Terminal:
        double = Terminal(answers)
        monkeypatch.setattr(sys, "stdin", double)
        return double

    return answering


@pytest.fixture
def printer(monkeypatch: pytest.MonkeyPatch) -> Printer:
    """既定のプリンターの代役を、printing.send に替えて置く。"""
    double = Printer()
    monkeypatch.setattr(printing, "send", double.send)
    return double


@pytest.fixture
def aoba(home: Path) -> Issuer:
    """ガイドの答えで、株式会社あおば事務用品の発行者情報を残したあとのホームフォルダー。"""
    return save_aoba()
```

`invoice/tests/e2e/test_scenarios.py` は、各鍵となる結果を名指しする。

```python
"""経理チームが、ガイドだけを頼りに、明細からコマンド一つで請求書を印刷する E2E ケース。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import command, issuer
from tests.given import (
    AOBA,
    AOBA_ANSWERS,
    AOBA_LABELS,
    README_PAPER,
    README_ROWS,
    Printer,
    Terminal,
    asked,
    billed,
    csv,
    paper,
    printed,
)

supports = pytest.mark.supports

MONTH_ROWS = (
    "株式会社ひかり設計,2026-11-02,トナーカートリッジ 黒,2,本,12800,10%",
    "株式会社やまびこ食品,2026-11-04,ミネラルウォーター 2L 6本入,7,箱,1180,8%",
    "株式会社みなと商事,2026-11-05,コピー用紙 A4 500枚,10,箱,2800,10%",
    "株式会社ひかり設計,2026-11-09,コピー用紙 A3 500枚,3,箱,4200,10%",
    "株式会社みなと商事,2026-11-12,ドリップコーヒー 100袋入,3,箱,4500,8%",
    "株式会社ひかり設計,2026-11-13,プリンター用紙 B4 500枚,2,箱,3600,10%",
    "株式会社ひかり設計,2026-11-16,緑茶ティーバッグ 50袋入,6,箱,980,8%",
    "株式会社やまびこ食品,2026-11-18,ドリップコーヒー 100袋入,2,箱,4500,8%",
    "株式会社みなと商事,2026-11-20,ボールペン 黒 10本入,5,箱,1200,10%",
    "株式会社やまびこ食品,2026-11-24,紙コップ 205ml 100個入,10,袋,450,10%",
    "株式会社みなと商事,2026-11-25,クリアファイル A4 100枚入,4,箱,1350,10%",
    "株式会社みなと商事,2026-11-26,ホッチキス針 No.10 20箱入,2,箱,1500,10%",
    "株式会社ひかり設計,2026-11-27,付箋 75mm 10冊入,7,箱,640,10%",
    "株式会社やまびこ食品,2026-11-30,段ボール箱 120サイズ 10枚入,3,束,2350,10%",
)
"""あおば事務用品が三つの取引先に売った、11 月分の明細の行。"""

MONTH_PAPERS = {
    "株式会社みなと商事 御中": ("61,220", "10% 42,400 4,240", "8%(軽減税率) 13,500 1,080"),
    "株式会社ひかり設計 御中": ("61,218", "10% 49,880 4,988", "8%(軽減税率) 5,880 470"),
    "株式会社やまびこ食品 御中": ("31,345", "10% 11,550 1,155", "8%(軽減税率) 17,260 1,380"),
}
"""11 月分の明細から、取引先ごとに出る請求書のご請求金額と、税率ごとの合計の行。"""


def printed_month(out: str, printer: Printer) -> None:
    """11 月分の明細から、三つの取引先の請求書が、それぞれ正しい額で一枚ずつ出たこと。"""
    shown = billed(out)
    assert {name: amount for name, (_, amount) in shown.items()} == {
        name: amount for name, (amount, *_) in MONTH_PAPERS.items()
    }
    assert {number for number, _ in shown.values()} == {"2026-11-001", "2026-11-002", "2026-11-003"}
    assert printed(3) in out
    assert len(printer.sent) == 3
    for name, (amount, *totals) in MONTH_PAPERS.items():
        [text] = [paper(each) for each in printer.sent if name in paper(each)]
        number, _ = shown[name]
        for line in (
            "株式会社あおば事務用品",
            "登録番号: T1234567890123",
            f"請求書番号: {number}",
            "発行日: 2026年11月30日",
            f"ご請求金額(税込): {amount} 円",
            "お支払期限: 2026年12月31日",
            "お振込先: さくら銀行 本店営業部 普通 1234567 カ)アオバジムヨウヒン",
            *totals,
            f"合計(税込): {amount} 円",
        ):
            assert line in text


@supports("KR1.1")
def test_初めての月に一か月分の明細から取引先ごとの請求書を自分たちで印刷できる(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: invoice を入れたばかりのノートPCと、三つの取引先の 11 月分の明細。
    path = ledger(csv(*MONTH_ROWS))
    terminal(*AOBA_ANSWERS)
    # When: 利用者が明細のファイルを渡してコマンドを一つ打ち、尋ねられた事柄に答える。
    code = command.main([str(path)])
    # Then: 事柄を一度ずつ尋ね、取引先ごとの請求書を印刷し、発行者情報を残す。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == list(AOBA_LABELS)
    printed_month(out, printer)
    assert issuer.load() == AOBA


@supports("KR1.1")
def test_明細の誤りを示されたとおりに直して打ち直すと印刷できる(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 取引日と数量を打ち間違えた、11 月分の明細。
    wrong = list(MONTH_ROWS)
    wrong[3] = wrong[3].replace("2026-11-09", "2026-11-31")
    wrong[12] = wrong[12].replace(",7,箱,", ",七,箱,")
    path = ledger(csv(*wrong))
    terminal()
    # When: 利用者がコマンドを打つ。
    first = command.main([str(path)])
    # Then: 誤りの行と列と値をすべて示し、何も尋ねず、何も印刷しない。
    out = capsys.readouterr().out
    assert first == 1
    for line, column, given in ((5, "取引日", "2026-11-31"), (14, "数量", "七")):
        assert str(line) in out
        assert column in out
        assert given in out
    assert asked(out) == []
    assert printer.sent == []
    # When: 利用者が示されたとおりに直し、同じコマンドを打ち直す。
    path.write_text(csv(*MONTH_ROWS), encoding="utf-8")
    terminal(*AOBA_ANSWERS)
    second = command.main([str(path)])
    # Then: はじめから正しく打ったときと同じく、取引先ごとの請求書が出る。
    out = capsys.readouterr().out
    assert second == 0
    printed_month(out, printer)


@supports("KR1.2")
def test_翌月からは明細を渡すコマンド一つで何も尋ねずに印刷まで進む(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 11 月分を、初回の答えとともに印刷したあと。
    terminal(*AOBA_ANSWERS)
    assert command.main([str(ledger(csv(*README_ROWS)))]) == 0
    november = billed(capsys.readouterr().out)["株式会社みなと商事 御中"]
    assert november == ("2026-11-001", "51,980")
    assert all(line in paper(printer.sent[0]) for line in README_PAPER)
    printer.sent.clear()
    december = ledger(
        csv(
            "株式会社みなと商事,2026-12-03,コピー用紙 A4 500枚,8,箱,2800,10%",
            "株式会社みなと商事,2026-12-10,ドリップコーヒー 100袋入,2,箱,4500,8%",
        ),
        name="2026年12月分明細.csv",
    )
    terminal()
    # When: 利用者が 12 月分の明細を渡して、コマンドを一つ打つ。
    code = command.main([str(december)])
    # Then: 何も尋ねずに、12 月の最初の番号の請求書を一枚印刷する。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == []
    assert billed(out) == {"株式会社みなと商事 御中": ("2026-12-001", "34,360")}
    assert printed(1) in out
    [document] = printer.sent
    for line in (
        "請求書番号: 2026-12-001",
        "発行日: 2026年12月31日",
        "お支払期限: 2027年1月31日",
        "10% 22,400 2,240",
        "8%(軽減税率) 9,000 720",
        "合計(税込): 34,360 円",
    ):
        assert line in paper(document)
```

## 結合ケース

結合ケースは、部品をスケルトンのインターフェースどうしでつなぎ、既定のプリンターだけを代役に替える。

各ケースは、確かめるストーリー、原則の項目、データ、コンポーネントを `supports` で名指しする。

`invoice/tests/integration/test_print.py` は、S1 の道筋と、その原則と決めごとを確かめる。

```python
"""S1: 明細から請求書を印刷する道筋と、その原則と決めごとの結合ケース。"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import billing, command, issuer, layout, ledger as ledger_module, numbering, printing
from invoice.issuer import Issuer
from tests.given import (
    AOBA,
    AOBA_ANSWERS,
    INCLUDED_HEADER,
    MINATO,
    NOVEMBER,
    README_INVOICE,
    README_PAPER,
    README_ROWS,
    Printer,
    Terminal,
    asked,
    billed,
    csv,
    paper,
    printed,
    save_aoba,
)

supports = pytest.mark.supports


@supports(
    "S1", "P2.3", "P2.6", "P3.1",
    "明細", "明細行", "発行者情報", "請求書", "税率ごとの合計", "印刷用の文書",
    "コマンド", "明細の読み取り", "発行者情報の保管", "請求の計算", "番号の採番", "請求書の組版", "印刷",
)
def test_明細から請求書が印刷され番号と金額と枚数が示される(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報を残したあとの、ガイドの 11 月分の明細。
    path = ledger(csv(*README_ROWS))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 一枚の請求書を既定のプリンターに送り、番号と金額と、プリンターの名前と枚数を示す。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == []
    assert billed(out) == {"株式会社みなと商事 御中": ("2026-11-001", "51,980")}
    assert out.endswith(printed(1) + "\n")
    [document] = printer.sent
    assert document.sheets == 1
    for line in README_PAPER:
        assert line in paper(document)


@supports("S1", "P3.4", "P3.6", "P3.7", "P3.8", "P3.9")
def test_取引先と締めの期間ごとに一枚ずつ印刷される(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 20日締め翌月10日払いの発行者と、締め日の前後にまたがる二つの取引先の明細。
    save_aoba(payment_terms="20日締め翌月10日払い")
    path = ledger(
        csv(
            "株式会社みなと商事,2026-11-20,コピー用紙 A4 500枚,10,箱,2800,10%",
            "株式会社ひかり設計,2026-11-05,トナーカートリッジ 黒,2,本,12800,10%",
            "株式会社みなと商事,2026-11-21,ボールペン 黒 10本入,5,箱,1200,10%",
        )
    )
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 取引先と締めの期間の組ごとに一枚ずつ、その期間の行だけを載せ、発行日の月ごとの番号で印刷する。
    out = capsys.readouterr().out
    assert code == 0
    assert printed(3) in out
    texts = [paper(each) for each in printer.sent]
    expected = (
        ("株式会社みなと商事 御中", "2026年11月20日", "2026年12月10日", "30,800", "コピー用紙", "ボールペン"),
        ("株式会社みなと商事 御中", "2026年12月20日", "2027年1月10日", "6,600", "ボールペン", "コピー用紙"),
        ("株式会社ひかり設計 御中", "2026年11月20日", "2026年12月10日", "28,160", "トナーカートリッジ", "コピー用紙"),
    )
    assert len(texts) == 3
    assert {each.split("請求書番号: ")[1].split()[0] for each in texts} == {"2026-11-001", "2026-11-002", "2026-12-001"}
    for name, issued, due, amount, kept, left in expected:
        [text] = [each for each in texts if name in each and f"発行日: {issued}" in each]
        assert f"お支払期限: {due}" in text
        assert f"ご請求金額(税込): {amount} 円" in text
        assert kept in text
        assert left not in text


@supports("S1", "P3.2", "税率ごとの合計")
def test_消費税額は税率ごとに一度だけ切り捨てて載る(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 行ごとに切り捨てると 264 円、合計で切り捨てると 266 円になる、軽減税率の三行。
    path = ledger(
        csv(
            "株式会社みなと商事,2026-11-02,緑茶ティーバッグ 50袋入,1,箱,1111,8%",
            "株式会社みなと商事,2026-11-09,緑茶ティーバッグ 50袋入,1,箱,1111,8%",
            "株式会社みなと商事,2026-11-16,緑茶ティーバッグ 50袋入,1,箱,1111,8%",
        )
    )
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 消費税額は税率ごとの対象額から一度だけ切り捨てた 266 円になる。
    assert code == 0
    assert billed(capsys.readouterr().out) == {"株式会社みなと商事 御中": ("2026-11-001", "3,599")}
    text = paper(printer.sent[0])
    assert "8%(軽減税率) 3,333 266" in text
    assert "合計(税込): 3,599 円" in text


@supports("S1", "P3.3")
def test_税込の単価の明細では税込の合計から消費税額が出る(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 単価が税込の明細。
    path = ledger(
        csv(
            "株式会社みなと商事,2026-11-05,コピー用紙 A4 500枚,3,箱,1100,10%",
            "株式会社みなと商事,2026-11-12,ドリップコーヒー 100袋入,1,箱,1080,8%",
            "株式会社みなと商事,2026-11-20,ボールペン 黒 10本入,1,箱,1000,10%",
            header=INCLUDED_HEADER,
        )
    )
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 税率ごとの税込の対象額から消費税額を出し、税込の対象額の和を請求する。
    assert code == 0
    assert billed(capsys.readouterr().out) == {"株式会社みなと商事 御中": ("2026-11-001", "5,380")}
    text = paper(printer.sent[0])
    for line in (
        "取引日 品目 数量 単価(税込) 税率 金額(税込)",
        "税率 対象額(税込) 消費税額",
        "10% 4,300 390",
        "8%(軽減税率) 1,080 80",
        "合計(税込): 5,380 円",
    ):
        assert line in text


@supports("S1", "P3.1", "請求の計算", "請求書の組版")
def test_画面と紙面の金額は請求の計算が決めた額と同じ(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 二つの取引先の明細。
    path = ledger(
        csv(*README_ROWS, "株式会社ひかり設計,2026-11-16,緑茶ティーバッグ 50袋入,6,箱,980,8%")
    )
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 画面と紙面に、請求の計算が決めた番号と額がそのまま載る。
    shown = billed(capsys.readouterr().out)
    decided = {
        f"{each.customer.name} {each.customer.honorific}": (each.number, f"{each.amount:,}")
        for each in billing.bill(ledger_module.read(path), aoba)
    }
    assert code == 0
    assert shown == decided
    for name, (number, amount) in decided.items():
        [text] = [paper(each) for each in printer.sent if name in paper(each)]
        assert f"請求書番号: {number}" in text
        assert f"ご請求金額(税込): {amount} 円" in text
        assert f"合計(税込): {amount} 円" in text


@supports("S1", "P3.5", "発行記録", "番号の採番")
def test_同じ明細を二度印刷しても同じ請求書番号になる(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 一度印刷した、ガイドの 11 月分の明細。
    path = ledger(csv(*README_ROWS))
    terminal()
    assert command.main([str(path)]) == 0
    first = capsys.readouterr().out
    # When: 利用者が同じ明細で、もう一度印刷する。
    terminal()
    code = command.main([str(path)])
    # Then: 前と同じ番号の、同じ中身の請求書が出る。
    second = capsys.readouterr().out
    assert code == 0
    assert billed(second) == billed(first) == {"株式会社みなと商事 御中": ("2026-11-001", "51,980")}
    assert paper(printer.sent[1]) == paper(printer.sent[0])
    assert numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end) == "2026-11-001"


@supports("S1", "P2.3", "印刷")
def test_印刷システムに触れるのは印刷だけ(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: printing.send を代役に替え、印刷システムのコマンドを呼ぶと失敗するノートPC。
    printing_commands = {"lp", "lpr", "lpstat", "lpoptions", "lpadmin", "cancel"}

    class Guarded(subprocess.Popen):  # type: ignore[type-arg]
        def __init__(self, args, *rest, **named):  # type: ignore[no-untyped-def]
            first = args if isinstance(args, str | bytes | os.PathLike) else next(iter(args))
            assert os.path.basename(os.fsdecode(first)).split()[0] not in printing_commands
            super().__init__(args, *rest, **named)

    monkeypatch.setattr(subprocess, "Popen", Guarded)
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then: ほかの部品は印刷システムに触れず、紙面は代役にだけ届く。
    assert code == 0
    assert len(printer.sent) == 1


@supports("S1", "P2.2", "発行者情報", "発行記録")
def test_どのフォルダーで打っても同じ発行者情報と番号を使う(
    home: Path,
    tmp_path: Path,
    terminal: Callable[..., Terminal],
    printer: Printer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 11 月分を、あるフォルダーで初回の答えとともに印刷したあと。
    november, december = tmp_path / "11月", tmp_path / "12月"
    for folder in (november, december):
        folder.mkdir()
    (november / "明細.csv").write_text(csv(*README_ROWS), encoding="utf-8")
    (december / "明細.csv").write_text(
        csv("株式会社みなと商事,2026-12-03,コピー用紙 A4 500枚,8,箱,2800,10%"), encoding="utf-8"
    )
    monkeypatch.chdir(november)
    terminal(*AOBA_ANSWERS)
    assert command.main(["明細.csv"]) == 0
    first = billed(capsys.readouterr().out)
    # When: 利用者が別のフォルダーで、12 月分の明細を渡す。
    monkeypatch.chdir(december)
    terminal()
    code = command.main(["明細.csv"])
    # Then: 何も尋ねず、11 月と重ならない番号で印刷する。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == []
    assert billed(out)["株式会社みなと商事 御中"][0] != first["株式会社みなと商事 御中"][0]
    assert issuer.load() == AOBA


@supports("P1.2", "コマンド")
def test_利用者と言葉を交わすのはコマンドだけ(
    aoba: Issuer,
    ledger: Callable[..., Path],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 誤りのある明細と、誤りのない明細。
    wrong = ledger(csv("株式会社みなと商事,2026-11-31,コピー用紙 A4 500枚,10,箱,2800,10%"), name="誤り.csv")
    right = ledger(csv(*README_ROWS))
    # When: コマンドのほかの部品を、断るときも含めて一つずつ呼ぶ。
    with pytest.raises(ledger_module.LedgerRefused):
        ledger_module.read(wrong)
    with pytest.raises(issuer.AnswerRefused):
        issuer.check("payment_terms", "末締め")
    invoices = billing.bill(ledger_module.read(right), aoba)
    printing.print_documents(layout.typeset(invoices))
    # Then: どの部品も、端末に何も示さない。
    assert capsys.readouterr() == ("", "")
    assert [each.lines for each in invoices] == [README_INVOICE.lines]
```

`invoice/tests/integration/test_start.py` は、S2 の道筋を確かめる。

```python
"""S2: 自分たちだけで使い始める道筋の結合ケース。"""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from invoice import command

supports = pytest.mark.supports

PRODUCT = Path(__file__).resolve().parents[2]
"""invoice の一式のフォルダー。"""


def uv(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """ガイドのインストーラーの uv を、ケースだけの置き場で動かす。"""
    env = os.environ | {
        "UV_TOOL_DIR": str(tmp_path / "tools"),
        "UV_TOOL_BIN_DIR": str(tmp_path / "bin"),
        "UV_CACHE_DIR": str(tmp_path / "cache"),
    }
    return subprocess.run(["uv", *args], capture_output=True, text=True, env=env, check=False)


@supports("S2")
def test_版を尋ねると版が示される(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: invoice を入れたあと。
    monkeypatch.setattr(sys, "argv", ["invoice", "--version"])
    # When: 利用者が版を尋ねる。
    code = command.main()
    # Then: ガイドのとおりの版を示す。
    assert code == 0
    assert capsys.readouterr() == ("invoice 0.1.0\n", "")


@supports("S2", "P1.1")
def test_配布物を入れると版が示され書体もともに入る(tmp_path: Path) -> None:
    # Given: invoice の一式から作った配布物。
    built = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path / "dist"), str(PRODUCT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert built.returncode == 0, built.stderr
    [wheel] = (tmp_path / "dist").glob("invoice-0.1.0-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        fonts = [name for name in archive.namelist() if name.startswith("invoice/fonts/")]
    # When: 利用者が配布物を入れ、版を尋ねる。
    installed = uv(tmp_path, "tool", "install", str(wheel))
    version = subprocess.run(
        [str(tmp_path / "bin" / "invoice"), "--version"], capture_output=True, text=True, check=False
    )
    # Then: 書体をともに入れ終え、ガイドのとおりの版を示す。
    assert fonts != []
    assert installed.returncode == 0, installed.stderr
    assert (version.returncode, version.stdout) == (0, "invoice 0.1.0\n")
```

`invoice/tests/integration/test_issuer.py` は、S3 の道筋と、その原則と決めごとを確かめる。

```python
"""S3: 発行者の情報を一度だけ伝える道筋と、その原則と決めごとの結合ケース。"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import command, issuer, periods, place
from invoice.issuer import Issuer, PaymentTerms
from tests.given import (
    AOBA,
    AOBA_ANSWERS,
    AOBA_LABELS,
    README_ROWS,
    Printer,
    Terminal,
    asked,
    csv,
    files,
    paper,
)

supports = pytest.mark.supports


def refusal(item: issuer.IssuerItem, answer: str) -> issuer.AnswerFix:
    """答えを確かめさせたときの、直すところ。"""
    with pytest.raises(issuer.AnswerRefused) as refused:
        issuer.check(item, answer)
    return refused.value.fix


@supports("S3", "P2.1", "P2.4", "発行者情報", "発行者情報の保管")
def test_初回は事柄を順に尋ねすべての答えがそろってから残す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、ガイドの明細。
    path = ledger(csv(*README_ROWS))
    terminal(*AOBA_ANSWERS)
    # When: 利用者が明細のファイルを渡し、尋ねられた事柄に答える。
    code = command.main([str(path)])
    # Then: 事柄を一度ずつ順に尋ね、答えを発行者情報として残し、印刷まで進む。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == list(AOBA_LABELS)
    assert issuer.load() == AOBA
    assert len(printer.sent) == 1


@supports("S3", "P2.5")
def test_明細に直すところがあれば初回も何も尋ねずに止まる(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、取引日に誤りのある明細。
    path = ledger(csv("株式会社みなと商事,2026-11-31,コピー用紙 A4 500枚,10,箱,2800,10%"))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 何も尋ねず、何も残さず、何も印刷せずに止まる。
    out = capsys.readouterr().out
    assert code == 1
    assert asked(out) == []
    assert "2026-11-31" in out
    assert isinstance(issuer.load(), tuple)
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("S3", "P2.4")
def test_答えずに止めると何も残さず次は最初から尋ねる(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 初回に、三つの事柄に答えたあと、四つ目で利用者が Ctrl+C で止める。
    path = ledger(csv(*README_ROWS))
    terminal(*AOBA_ANSWERS[:3])
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 130 で止まり、発行者情報を何も残さず、何も印刷しない。
    out = capsys.readouterr().out
    assert code == 130
    assert asked(out) == list(AOBA_LABELS[:4])
    assert files(place.folder()) == {}
    assert printer.sent == []
    # When: 利用者がもう一度打つ。
    terminal(*AOBA_ANSWERS)
    again = command.main([str(path)])
    # Then: 初回として最初の事柄から尋ね直す。
    assert again == 0
    assert asked(capsys.readouterr().out) == list(AOBA_LABELS)


@supports("S3", "P1.5", "P3.10", "P3.11", "P3.12", "直すところ")
def test_形に合わない答えは例を示して同じ事柄を尋ね直す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 支払条件に、形に合わない答えを三つ続けてから、正しい答えを打つ利用者。
    wrong = ("月末締め当月末払い", "29日締め翌月10日払い", "20日締め翌月10日")
    path = ledger(csv(*README_ROWS))
    terminal(*AOBA_ANSWERS[:2], *wrong, *AOBA_ANSWERS[2:])
    # When: 利用者が明細のファイルを渡し、尋ねられた事柄に答える。
    code = command.main([str(path)])
    # Then: 答えごとに受け付ける形の例を示し、支払条件だけを尋ね直して、正しい答えを残す。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == [*AOBA_LABELS[:2], *[AOBA_LABELS[2]] * 4, *AOBA_LABELS[3:]]
    for answer in wrong:
        assert refusal("payment_terms", answer).expected in out
    assert issuer.load() == AOBA


@supports("S3", "P2.2")
def test_二回目からは何も尋ねずに印刷まで進む(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報を残したあと。
    path = ledger(csv(*README_ROWS))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 何も尋ねずに印刷まで進む。
    assert code == 0
    assert asked(capsys.readouterr().out) == []
    assert len(printer.sent) == 1


@supports("S3", "P3.9", "P3.10", "発行者情報の保管", "請求の計算")
def test_支払条件は三つの値で保たれ期間と期限はその値から決まる(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
) -> None:
    # Given: 初回に、支払条件を「20日締め翌月10日払い」と答える利用者。
    answers = (*AOBA_ANSWERS[:2], "20日締め翌月10日払い", *AOBA_ANSWERS[3:])
    terminal(*answers)
    # When: 利用者がガイドの明細を渡す。
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then: 支払条件は三つの値で残り、請求書の日付はその値から決まる。
    terms = PaymentTerms(closing_day=20, month=1, payment_day=10)
    loaded = issuer.load()
    assert code == 0
    assert isinstance(loaded, Issuer) and loaded.payment_terms == terms
    text = paper(printer.sent[0])
    assert "発行日: 2026年11月20日" in text
    assert "お支払期限: 2026年12月10日" in text
    day, read = datetime.date(2026, 11, 5), issuer.check("payment_terms", answers[2])
    assert isinstance(read, PaymentTerms)
    assert periods.dates_of(day, read) == periods.dates_of(day, terms)
```

`invoice/tests/integration/test_recover.py` は、S4 の道筋と、その原則と決めごとを確かめる。

```python
"""S4: つまずいても自分で直して進む道筋と、その原則と決めごとの結合ケース。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import command, ledger as ledger_module, place
from invoice.issuer import Issuer
from tests.given import README_ROWS, Printer, Terminal, billed, csv, files, paper, save_aoba

supports = pytest.mark.supports


@supports("S4", "P1.2", "P1.3", "直すところ", "明細の読み取り")
def test_明細の直すところをすべて示し何も印刷しない(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 二つの行の三つの列に誤りのある明細。
    path = ledger(
        csv(
            "株式会社みなと商事,2026-11-31,コピー用紙 A4 500枚,10,箱,2800,10%",
            README_ROWS[1],
            "株式会社みなと商事,2026-11-20,ボールペン 黒 10本入,五,箱,1200,5%",
        )
    )
    with pytest.raises(ledger_module.LedgerRefused) as refused:
        ledger_module.read(path)
    kept = files(place.folder())
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: すべての直すところを、行と列と値と例とともに一度に示し、何も印刷しない。
    out = capsys.readouterr().out
    assert code == 1
    assert {(fix.line, fix.column, fix.given) for fix in refused.value.fixes} == {
        (2, "取引日", "2026-11-31"),
        (4, "数量", "五"),
        (4, "税率", "5%"),
    }
    for fix in refused.value.fixes:
        for shown in (str(fix.line), fix.column, fix.given, fix.expected):
            assert shown is not None and shown in out
    assert printer.sent == []
    assert files(place.folder()) == kept


@supports("S4", "P1.4")
def test_示されたとおり直して打ち直すとはじめから正しいときと同じ請求書が出る(
    home: Path,
    tmp_path: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: はじめから正しい明細で印刷した、別の利用者の請求書。
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("HOME", str(other))
    save_aoba()
    path = ledger(csv(*README_ROWS))
    terminal()
    assert command.main([str(path)]) == 0
    right = (billed(capsys.readouterr().out), paper(printer.sent.pop()))
    # Given: 取引日に誤りのある明細で止まったあとの利用者。
    monkeypatch.setenv("HOME", str(home))
    save_aoba()
    path.write_text(csv(README_ROWS[0].replace("2026-11-05", "2026-11-31"), *README_ROWS[1:]), encoding="utf-8")
    terminal()
    assert command.main([str(path)]) == 1
    capsys.readouterr()
    # When: 利用者が示されたとおりに直し、同じコマンドを打ち直す。
    path.write_text(csv(*README_ROWS), encoding="utf-8")
    terminal()
    code = command.main([str(path)])
    # Then: はじめから正しく打ったときと同じ請求書が出る。
    assert code == 0
    assert (billed(capsys.readouterr().out), paper(printer.sent.pop())) == right


@supports("S4", "P1.2", "P1.4", "印刷")
def test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 既定のプリンターのないノートPC。
    printer.refuse_at, printer.problem = 0, "no_default_printer"
    path = ledger(csv(*README_ROWS))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: プリンターの整え方を示し、何も印刷せずに止まる。
    out = capsys.readouterr().out
    assert code == 1
    assert "プリンター" in out
    assert printer.sent == []
    # When: 利用者がプリンターを整えてから、同じコマンドを打ち直す。
    printer.refuse_at = None
    terminal()
    again = command.main([str(path)])
    # Then: 番号を飛ばさず、ガイドのとおりの番号で印刷する。
    assert again == 0
    assert billed(capsys.readouterr().out) == {"株式会社みなと商事 御中": ("2026-11-001", "51,980")}
    assert len(printer.sent) == 1


@supports("S4", "P1.2")
def test_送る途中で送れなくなると整え方を示して止まる(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 一枚目を送ったあと、印刷システムが断るノートPCと、二つの取引先の明細。
    printer.refuse_at = 1
    path = ledger(
        csv(*README_ROWS, "株式会社ひかり設計,2026-11-16,緑茶ティーバッグ 50袋入,6,箱,980,8%")
    )
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: プリンターの整え方を示して止まり、二枚目は送らない。
    assert code == 1
    assert "プリンター" in capsys.readouterr().out
    assert len(printer.sent) == 1


@supports("S1", "S3", "発行者情報の保管")
def test_置き場のファイルが壊れていると直し方を示し何も印刷しない(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 残した発行者情報のファイルが壊れたノートPC。
    broken = list(files(place.folder()))
    for each in broken:
        each.write_bytes(b"\x00broken")
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then: どのファイルが問題かを示し、何も尋ねず、何も印刷せずに止まる。
    out = capsys.readouterr().out
    assert code == 1
    assert any(str(each) in out for each in broken)
    assert printer.sent == []
```

## 単体ケース

単体ケースは、スケルトンの各インターフェースを、契約が分けるクラスと状態の移りごとに確かめる。

各ケースは、支える結合ケースを `supports` で名指しする。

`invoice/tests/unit/test_command.py` は、`command.main` を確かめる。

```python
"""コマンド (command.main) の単体ケース。"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import command, issuer, ledger as ledger_module, place
from invoice.issuer import Issuer
from tests.given import (
    AOBA,
    AOBA_ANSWERS,
    AOBA_LABELS,
    ITEMS,
    README_ROWS,
    Printer,
    Terminal,
    asked,
    billed,
    checked,
    csv,
    files,
    printed,
)

supports = pytest.mark.supports


@supports("test_版を尋ねると版が示される")
def test_版を尋ねると版だけを示して0を返す(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Given: 何も残していないノートPC。
    # When
    code = command.main(["--version"])
    # Then
    assert code == 0
    assert capsys.readouterr() == ("invoice 0.1.0\n", "")
    assert files(place.folder()) == {}


@supports("test_版を尋ねると版が示される")
def test_引数を渡さずに呼ぶとコマンドラインの引数を使う(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: 利用者が端末で `invoice --version` と打った状態。
    monkeypatch.setattr(sys, "argv", ["invoice", "--version"])
    # When
    code = command.main()
    # Then
    assert code == 0
    assert capsys.readouterr() == ("invoice 0.1.0\n", "")
    assert files(place.folder()) == {}


@supports("test_版を尋ねると版が示される")
@pytest.mark.parametrize("argv", [[], ["2026年11月分明細.csv", "2026年12月分明細.csv"], ["--version", "x.csv"]])
def test_引数が明細一つでも版でもなければ使い方を示して2を返す(
    home: Path, printer: Printer, argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: 何も残していないノートPC。
    # When
    code = command.main(argv)
    # Then
    out, err = capsys.readouterr()
    assert code == 2
    assert out + err != ""
    assert asked(out + err) == []
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_ない明細のファイルではそのパスを示して1を返す(
    aoba: Issuer, tmp_path: Path, terminal: Callable[..., Terminal], printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: ないファイルのパス。
    missing = tmp_path / "2026年11月分明細.csv"
    terminal()
    # When
    code = command.main([str(missing)])
    # Then
    assert code == 1
    assert str(missing) in capsys.readouterr().out
    assert printer.sent == []


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_読めない明細のファイルではそのパスとUTF8のCSVでの保存し直し方を示し何も尋ねずに1を返す(
    home: Path, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、Shift_JIS で保存したガイドの明細。
    path = ledger(csv(*README_ROWS), encoding="shift_jis")
    with pytest.raises(ledger_module.LedgerRefused) as refused:
        ledger_module.read(path)
    terminal()
    # When
    code = command.main([str(path)])
    # Then: ファイルを読めないことと、UTF-8 の CSV で保存し直す手順を示し、何も尋ねず、何も残さず、何も印刷しない。
    out = capsys.readouterr().out
    assert [fix.problem for fix in refused.value.fixes] == ["unreadable"]
    assert code == 1
    assert str(path) in out
    assert "UTF-8" in out
    assert "CSV" in out
    assert asked(out) == []
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_見出しの行しかない明細では行がないことと一行の例を示し何も尋ねずに1を返す(
    home: Path, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、見出しの行だけを保存した明細。
    path = ledger(csv())
    with pytest.raises(ledger_module.LedgerRefused) as refused:
        ledger_module.read(path)
    [fix] = refused.value.fixes
    terminal()
    # When
    code = command.main([str(path)])
    # Then: 明細に行がないことを、そのまま書き足せる一行の例とともに示し、何も尋ねず、何も残さず、何も印刷しない。
    out = capsys.readouterr().out
    assert fix.problem == "no_rows"
    assert code == 1
    assert str(path) in out
    assert fix.expected != "" and fix.expected in out
    assert asked(out) == []
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_明細の直すところをすべて示し何も印刷しない")
@pytest.mark.parametrize(
    "wrong",
    [
        "株式会社みなと商事,2026-11-31,コピー用紙 A4 500枚,10,箱,2800,10%",
        "株式会社みなと商事,2026-11-05,コピー用紙 A4 500枚,,箱,2800,10%",
    ],
)
def test_受け付けない値の行がある明細ではその行と列と値と受け付ける例を示し何も尋ねずに1を返す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    wrong: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、二行目の取引日にない日付を書いたか、数量を空にした明細。
    path = ledger(csv(wrong))
    with pytest.raises(ledger_module.LedgerRefused) as refused:
        ledger_module.read(path)
    [fix] = refused.value.fixes
    terminal()
    # When
    code = command.main([str(path)])
    # Then: その行と列と、書かれていた値と、受け付ける形の例を示し、何も尋ねず、何も残さず、何も印刷しない。
    out = capsys.readouterr().out
    assert (fix.problem, fix.line) == ("bad_value", 2)
    assert code == 1
    assert str(path) in out
    rest = out.replace(str(path), "").replace(fix.given or "", "").replace(fix.expected, "")
    assert re.search(r"(?<![0-9])2(?![0-9])", rest), "誤りの行の番号 2 を示す"
    assert fix.column is not None and fix.column in out
    assert fix.given is None or fix.given in out
    assert fix.expected != "" and fix.expected in out
    assert asked(out) == []
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_初回は事柄を順に尋ねすべての答えがそろってから残す")
def test_発行者情報がない状態で明細を渡すとloadの事柄を順に尋ねて残す(
    home: Path, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報のない状態。
    questions = issuer.load()
    assert isinstance(questions, tuple)
    terminal(*AOBA_ANSWERS)
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == [question.label for question in questions] == list(AOBA_LABELS)
    assert issuer.load() == AOBA
    assert billed(out) == {"株式会社みなと商事 御中": ("2026-11-001", "51,980")}


@supports("test_二回目からは何も尋ねずに印刷まで進む")
def test_発行者情報がある状態で明細を渡すと何も尋ねずに印刷して0を返す(
    aoba: Issuer, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報のある状態。
    terminal()
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == []
    assert billed(out) == {"株式会社みなと商事 御中": ("2026-11-001", "51,980")}
    assert out.endswith(printed(1) + "\n")
    assert issuer.load() == AOBA
    assert len(printer.sent) == 1


@supports("test_答えずに止めると何も残さず次は最初から尋ねる")
@pytest.mark.parametrize("answered", [0, 7])
def test_尋ねる途中で止めると何も残さず130を返す(
    home: Path, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    answered: int, capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 最初の事柄か、最後の事柄で止める利用者。
    terminal(*AOBA_ANSWERS[:answered])
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    assert code == 130
    assert asked(capsys.readouterr().out) == list(AOBA_LABELS[: answered + 1])
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_形に合わない答えは例を示して同じ事柄を尋ね直す")
@pytest.mark.parametrize(("at", "wrong"), [(6, "123456"), (0, "")])
def test_断られた答えのあとは同じ事柄だけを尋ね直す(
    home: Path, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    at: int, wrong: str, capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 口座番号に 6 桁を答えるか、名称に何も打たずに Enter を押してから、正しく答える利用者。
    terminal(*AOBA_ANSWERS[:at], wrong, *AOBA_ANSWERS[at:])
    with pytest.raises(issuer.AnswerRefused) as refused:
        issuer.check(ITEMS[at], wrong)
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == [*AOBA_LABELS[: at + 1], *AOBA_LABELS[at:]]
    assert refused.value.fix.expected in out
    assert issuer.load() == AOBA


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行記録が壊れているとそのファイルを示して1を返す(
    aoba: Issuer, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 一度印刷したあと、発行者情報のほかに残ったファイルが壊れた状態。
    before = set(files(place.folder()))
    path = ledger(csv(*README_ROWS))
    terminal()
    assert command.main([str(path)]) == 0
    capsys.readouterr()
    records = [each for each in files(place.folder()) if each not in before]
    for each in records:
        each.write_bytes(b"\x00broken")
    printer.sent.clear()
    terminal()
    # When
    code = command.main([str(path)])
    # Then
    out = capsys.readouterr().out
    assert code == 1
    assert records != [] and any(str(each) in out for each in records)
    assert printer.sent == []


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行者情報のファイルを読めないとそのファイルを示し何も尋ねず何も印刷せずに1を返す(
    aoba: Issuer, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報を残したあと、そのファイルを読む権限がなくなった状態。
    if os.geteuid() == 0:
        pytest.skip("root はどのファイルも読める")
    locked = list(files(place.folder()))
    for each in locked:
        each.chmod(0)
    with pytest.raises(place.StoreRefused) as refused:
        issuer.load()
    terminal()
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then: 読めないファイルを示し、何も尋ねず、何も印刷せずに止まる。
    out = capsys.readouterr().out
    assert refused.value.fix.problem == "unreadable"
    assert code == 1
    assert str(refused.value.fix.path) in out
    assert asked(out) == []
    assert printer.sent == []


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_置き場に書けないと書けないことと直し方を示し何も残さず1を返す(
    home: Path, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: ホームフォルダーに書く権限がない、初めてのノートPCと、初回の答えをすべて打つ利用者。
    if os.geteuid() == 0:
        pytest.skip("root はどこにでも書ける")
    path = ledger(csv(*README_ROWS))
    home.chmod(0o500)
    try:
        with pytest.raises(place.StoreRefused) as refused:
            issuer.save(checked())
        terminal(*AOBA_ANSWERS)
        # When
        code = command.main([str(path)])
        # Then: すべての事柄を尋ねたあと、書けないファイルを示し、何も残さず、何も印刷せずに止まる。
        out = capsys.readouterr().out
        assert refused.value.fix.problem == "unwritable"
        assert code == 1
        assert asked(out) == list(AOBA_LABELS)
        assert str(refused.value.fix.path) in out
        assert files(place.folder()) == {}
        assert printer.sent == []
    finally:
        home.chmod(0o700)


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
@pytest.mark.parametrize("problem", ["no_default_printer", "send_failed"])
def test_印刷を断られるとプリンターの整え方を示して1を返す(
    aoba: Issuer, ledger: Callable[..., Path], terminal: Callable[..., Terminal], printer: Printer,
    problem: str, capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 既定のプリンターがないか、印刷システムが断るノートPC。
    printer.refuse_at, printer.problem = 0, problem
    terminal()
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 1
    assert "プリンター" in out
    assert "印刷しました" not in out
    assert printer.sent == []
    assert issuer.load() == AOBA
```

`invoice/tests/unit/test_ledger.py` は、`ledger.read` を確かめる。

```python
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
        path, "no_rows", None, None, None, ""
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
        path, "not_found", None, None, None, ""
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
        path, "unreadable", None, None, None, ""
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
    assert (fix.path, fix.problem, fix.line, fix.column, fix.given) == (
        path, "bad_value", 2, column, value or None
    )
    assert len(ledger_module.read(ledger(csv(with_cell(column, fix.expected))))) == 1


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_誤りのある行がいくつあってもすべての行を読み終えてすべての直すところを返す(
    ledger: Callable[..., Path]
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
```

`invoice/tests/unit/test_place.py` は、`place.folder` を確かめる。

```python
"""置き場 (place.folder) の単体ケース。"""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice import place

supports = pytest.mark.supports


@supports("test_どのフォルダーで打っても同じ発行者情報と番号を使う")
def test_置き場はホームフォルダーの中にありどのフォルダーで打っても同じ(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: 二つのフォルダー。
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    # When
    monkeypatch.chdir(first)
    here = place.folder()
    monkeypatch.chdir(second)
    there = place.folder()
    # Then
    assert here == there
    assert here.is_relative_to(home) and here != home
    assert not here.exists()


@supports("test_どのフォルダーで打っても同じ発行者情報と番号を使う")
def test_置き場は利用者のホームフォルダーに従う(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: 別の利用者のホームフォルダー。
    other = tmp_path / "other"
    other.mkdir()
    mine = place.folder()
    # When
    monkeypatch.setenv("HOME", str(other))
    theirs = place.folder()
    # Then
    assert theirs.is_relative_to(other)
    assert theirs != mine
```

`invoice/tests/unit/test_issuer.py` は、`issuer.load`、`issuer.check`、`issuer.save` を確かめる。

```python
"""発行者情報の保管 (issuer.load, issuer.check, issuer.save) の単体ケース。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from invoice import issuer, place
from invoice.issuer import AnswerFix, IssuerItem, PaymentTerms
from tests.given import AOBA, AOBA_LABELS, ITEMS, checked, files, save_aoba

supports = pytest.mark.supports


@supports("test_初回は事柄を順に尋ねすべての答えがそろってから残す")
def test_残していなければ尋ねる事柄をガイドの順と名前で返し例はそのまま受け付けられる(home: Path) -> None:
    # Given: 何も残していない状態。
    # When
    questions = issuer.load()
    # Then
    assert isinstance(questions, tuple)
    assert [(question.item, question.label) for question in questions] == list(zip(ITEMS, AOBA_LABELS, strict=True))
    for question in questions:
        issuer.check(question.item, question.example)
    assert files(place.folder()) == {}


@supports("test_二回目からは何も尋ねずに印刷まで進む")
def test_残したあとは残した発行者情報を返す(home: Path) -> None:
    # Given: 発行者情報を残した状態。
    saved = save_aoba()
    # When
    loaded = issuer.load()
    # Then
    assert loaded == saved == AOBA


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行者情報のファイルが壊れていれば壊れていると断る(home: Path) -> None:
    # Given: 発行者情報のファイルが壊れた状態。
    save_aoba()
    broken = list(files(place.folder()))
    for each in broken:
        each.write_bytes(b"\x00broken")
    # When
    with pytest.raises(place.StoreRefused) as refused:
        issuer.load()
    # Then
    assert refused.value.fix.problem == "broken"
    assert refused.value.fix.path in broken


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
@pytest.mark.parametrize("content", ["{}", "[]", '"株式会社あおば事務用品"'])
def test_発行者情報のファイルが読めても発行者情報の形に合わなければ壊れていると断る(home: Path, content: str) -> None:
    # Given: 発行者情報のファイルが、JSON としては読めるが、八つの事柄を持たない状態。
    save_aoba()
    broken = list(files(place.folder()))
    for each in broken:
        each.write_text(content, encoding="utf-8")
    # When
    with pytest.raises(place.StoreRefused) as refused:
        issuer.load()
    # Then
    assert refused.value.fix.problem == "broken"
    assert refused.value.fix.path in broken


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行者情報のファイルが読めなければ読めないと断る(home: Path) -> None:
    # Given: 発行者情報のファイルを読む権限がない状態。
    if os.geteuid() == 0:
        pytest.skip("root はどのファイルも読める")
    save_aoba()
    locked = list(files(place.folder()))
    for each in locked:
        each.chmod(0)
    # When
    with pytest.raises(place.StoreRefused) as refused:
        issuer.load()
    # Then
    assert refused.value.fix.problem == "unreadable"
    assert refused.value.fix.path in locked


@supports("test_初回は事柄を順に尋ねすべての答えがそろってから残す")
@pytest.mark.parametrize(
    ("item", "answer", "expected"),
    [
        ("name", "株式会社あおば事務用品", "株式会社あおば事務用品"),
        ("registration_number", "T1234567890123", "T1234567890123"),
        ("bank_name", "さくら銀行", "さくら銀行"),
        ("bank_branch", "本店営業部", "本店営業部"),
        ("account_type", "普通", "普通"),
        ("account_type", "当座", "当座"),
        ("account_number", "1234567", "1234567"),
        ("account_number", "0000000", "0000000"),
        ("account_holder", "カ)アオバジムヨウヒン", "カ)アオバジムヨウヒン"),
        ("registration_number", "Ｔ１２３４５６７８９０１２３", "T1234567890123"),
        ("account_number", "１２３４５６７", "1234567"),
        ("account_holder", "ｶ)ｱｵﾊﾞｼﾞﾑﾖｳﾋﾝ", "カ)アオバジムヨウヒン"),
    ],
)
def test_形に合う答えは全角の英数字を半角に半角カナを全角に読み替えて返し何も残さない(
    home: Path, item: IssuerItem, answer: str, expected: str
) -> None:
    # Given: 何も残していない状態。
    # When
    result = issuer.check(item, answer)
    # Then
    assert result == expected
    assert files(place.folder()) == {}


@supports("test_支払条件は三つの値で保たれ期間と期限はその値から決まる")
@pytest.mark.parametrize(
    ("answer", "terms"),
    [
        ("20日締め翌月10日払い", PaymentTerms(20, 1, 10)),
        ("月末締め翌月末払い", PaymentTerms("month_end", 1, "month_end")),
        ("月末締め翌月10日払い", PaymentTerms("month_end", 1, 10)),
        ("20日締め翌々月10日払い", PaymentTerms(20, 2, 10)),
        ("10日締め当月25日払い", PaymentTerms(10, 0, 25)),
        ("27日締め当月28日払い", PaymentTerms(27, 0, 28)),
        ("27日締め当月末払い", PaymentTerms(27, 0, "month_end")),
        ("1日締め翌月1日払い", PaymentTerms(1, 1, 1)),
        ("28日締め翌月28日払い", PaymentTerms(28, 1, 28)),
        ("２０日締め翌月１０日払い", PaymentTerms(20, 1, 10)),
    ],
)
def test_形どおりの支払条件は締め日と支払の月と支払日に読み取る(
    home: Path, answer: str, terms: PaymentTerms
) -> None:
    # Given: 何も残していない状態。
    # When
    result = issuer.check("payment_terms", answer)
    # Then
    assert result == terms
    assert files(place.folder()) == {}


@supports("test_形に合わない答えは例を示して同じ事柄を尋ね直す")
@pytest.mark.parametrize(
    ("item", "answer"),
    [
        *[(item, "") for item in ITEMS],
        ("registration_number", "T123456789012"),
        ("registration_number", "T12345678901234"),
        ("registration_number", "1234567890123"),
        ("registration_number", "TT234567890123"),
        ("payment_terms", "20日締め翌月10日"),
        ("payment_terms", "20日〆翌月10日払い"),
        ("payment_terms", "20日締め翌翌月10日払い"),
        ("payment_terms", "0日締め翌月10日払い"),
        ("payment_terms", "29日締め翌月10日払い"),
        ("payment_terms", "20日締め翌月29日払い"),
        ("payment_terms", "20日締め当月20日払い"),
        ("payment_terms", "20日締め当月10日払い"),
        ("payment_terms", "月末締め当月末払い"),
        ("payment_terms", "月末締め当月10日払い"),
        ("account_type", "貯蓄"),
        ("account_number", "123456"),
        ("account_number", "12345678"),
        ("account_number", "123456a"),
        ("account_holder", "株式会社あおば事務用品"),
        ("account_holder", "aoba"),
    ],
)
def test_形に合わない答えはその事柄と答えと受け付ける例で断り何も残さない(
    home: Path, item: IssuerItem, answer: str
) -> None:
    # Given: 何も残していない状態。
    # When
    with pytest.raises(issuer.AnswerRefused) as refused:
        issuer.check(item, answer)
    # Then
    fix = refused.value.fix
    assert (fix.item, fix.given) == (item, answer)
    assert isinstance(fix, AnswerFix)
    issuer.check(item, fix.expected)
    assert files(place.folder()) == {}


@supports("test_初回は事柄を順に尋ねすべての答えがそろってから残す")
def test_すべての答えをそろえて残させると発行者情報を返し次に読める(home: Path) -> None:
    # Given: 何も残していない状態。
    # When
    saved = issuer.save(checked())
    # Then
    assert saved == AOBA
    assert issuer.load() == AOBA


@supports("test_答えずに止めると何も残さず次は最初から尋ねる")
@pytest.mark.parametrize("missing", [ITEMS, ("account_holder",), ("name", "payment_terms")])
def test_答えが欠けていれば欠けた事柄を順に持って断り何も残さない(
    home: Path, missing: tuple[IssuerItem, ...]
) -> None:
    # Given: 事柄の一つ、いくつか、またはすべてが欠けた答え。
    answers = {item: answer for item, answer in checked().items() if item not in missing}
    # When
    with pytest.raises(issuer.AnswersIncomplete) as refused:
        issuer.save(answers)
    # Then
    assert refused.value.missing == missing
    assert isinstance(issuer.load(), tuple)
    assert files(place.folder()) == {}


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_書けない置き場には書けないと断り何も残さない(home: Path) -> None:
    # Given: ホームフォルダーに書く権限がない状態。
    if os.geteuid() == 0:
        pytest.skip("root はどこにでも書ける")
    home.chmod(0o500)
    try:
        # When
        with pytest.raises(place.StoreRefused) as refused:
            issuer.save(checked())
        # Then
        assert refused.value.fix.problem == "unwritable"
        assert refused.value.fix.path.is_relative_to(home)
        assert files(place.folder()) == {}
    finally:
        home.chmod(0o700)
```

`invoice/tests/unit/test_periods.py` は、`periods.dates_of` を確かめる。

```python
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
```

`invoice/tests/unit/test_billing.py` は、`billing.bill` を確かめる。

```python
"""請求の計算 (billing.bill) の単体ケース。"""

from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path

import pytest

from invoice import billing, numbering, place
from invoice.billing import Invoice, InvoiceLine, RateTotal
from invoice.issuer import PaymentTerms
from invoice.periods import Period
from tests.given import (
    AOBA,
    HIKARI,
    MINATO,
    MINATO_TOKYO,
    NOVEMBER,
    README_INVOICE,
    README_LEDGER_ROWS,
    files,
    row,
)

supports = pytest.mark.supports


def by_customer(invoices: tuple[Invoice, ...]) -> dict[tuple[str, Period], Invoice]:
    return {(each.customer.name, each.period): each for each in invoices}


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_一つの取引先の一つの期間の税抜の明細から一枚の請求書を返す(home: Path) -> None:
    # Given: ガイドの明細行と発行者情報。
    # When
    [invoice] = billing.bill(README_LEDGER_ROWS, AOBA)
    # Then
    assert invoice.number == numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end) == "2026-11-001"
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
    #   みなと商事の前の期間には、取引日が前後する行と、同じ取引日の二つの行がある。
    issuer = dataclasses.replace(AOBA, payment_terms=PaymentTerms(20, 1, 10))
    rows = (
        row(2, date(2026, 11, 21), "ボールペン 黒 10本入", 5, "箱", 1200, 10),
        row(3, date(2026, 11, 20), "コピー用紙 A4 500枚", 10, "箱", 2800, 10),
        row(4, date(2026, 11, 5), "トナーカートリッジ 黒", 2, "本", 12800, 10, customer=HIKARI),
        row(5, date(2026, 11, 1), "クリアファイル A4 100枚入", 4, "箱", 1350, 10),
        row(6, date(2026, 11, 6), "付箋 75mm 10冊入", 7, "箱", 640, 10, customer=MINATO_TOKYO),
        row(7, date(2026, 11, 1), "えんぴつ HB 12本入", 1, "箱", 640, 10),
    )
    first, second = Period(date(2026, 10, 21), date(2026, 11, 20)), Period(date(2026, 11, 21), date(2026, 12, 20))
    # When
    invoices = by_customer(billing.bill(rows, issuer))
    # Then: 行は取引日の順で、同じ取引日の行は明細の順のまま。
    assert {key: [line.row.line for line in each.lines] for key, each in invoices.items()} == {
        ("株式会社みなと商事", first): [5, 7, 3],
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
        ("株式会社みなと商事", first): 37444,
        ("株式会社みなと商事", second): 6600,
        ("株式会社ひかり設計", first): 28160,
        ("株式会社みなと商事東京支店", first): 4928,
    }
    assert {key[1]: each.number[:8] for key, each in invoices.items()} == {first: "2026-11-", second: "2026-12-"}
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
```

`invoice/tests/unit/test_numbering.py` は、`numbering.number` を確かめる。

```python
"""番号の採番 (numbering.number) の単体ケース。"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from invoice import numbering, place
from invoice.periods import Period
from tests.given import HIKARI, MINATO, MINATO_TOKYO, NOVEMBER, files

supports = pytest.mark.supports

OCTOBER = Period(date(2026, 10, 1), date(2026, 10, 31))
"""月末締めの、2026 年 10 月の締めの期間。"""


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_発行記録がない状態で初めての組には番号を付け発行記録に残す(home: Path) -> None:
    # Given: 発行記録のない状態。
    # When
    number = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    # Then
    assert number == "2026-11-001"
    assert files(place.folder()) != {}


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_初めての組には発行日の年月と年月ごとに001から数えた連番の番号を付ける(home: Path) -> None:
    # Given: 発行記録のない状態。
    # When: 11 月 30 日発行の二つの組、10 月 31 日発行の組、11 月 20 日発行の組、前の組の順に番号を求める。
    numbers = [
        numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end),
        numbering.number(HIKARI.name, NOVEMBER, NOVEMBER.end),
        numbering.number(MINATO.name, OCTOBER, OCTOBER.end),
        numbering.number(MINATO.name, Period(date(2026, 10, 21), date(2026, 11, 20)), date(2026, 11, 20)),
        numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end),
    ]
    # Then: 発行月ごとに 001 から数え、前に付けた組は数え直さない。
    assert numbers == ["2026-11-001", "2026-11-002", "2026-10-001", "2026-11-003", "2026-11-001"]


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
@pytest.mark.parametrize(
    ("issue_date", "expected"),
    [
        (date(2026, 12, 1), "2026-12-001"),
        (date(2026, 12, 31), "2026-12-001"),
        (date(2027, 1, 31), "2027-01-001"),
        (date(2026, 9, 30), "2026-09-001"),
    ],
)
def test_番号の年と月は発行日の年と2桁の月(home: Path, issue_date: date, expected: str) -> None:
    # Given: 発行記録のない状態と、月の初めか終わりか、年の変わり目か、一桁の月の発行日。
    period = Period(issue_date.replace(day=1), issue_date)
    # When
    number = numbering.number(MINATO.name, period, issue_date)
    # Then
    assert number == expected


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
def test_同じ月の十番目の組には3桁の連番010を付ける(home: Path) -> None:
    # Given: 11 月発行の九つの組に番号を付けた状態。
    before = [numbering.number(f"取引先 {i}", NOVEMBER, NOVEMBER.end) for i in range(1, 10)]
    # When
    tenth = numbering.number("取引先 10", NOVEMBER, NOVEMBER.end)
    # Then
    assert before[-1] == "2026-11-009"
    assert tenth == "2026-11-010"


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_前に付けた組にはいくつの組のあとでも前と同じ番号を返し発行記録を変えない(home: Path) -> None:
    # Given: 三つの組に番号を付けた状態。
    first = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    numbering.number(MINATO.name, OCTOBER, OCTOBER.end)
    numbering.number(HIKARI.name, NOVEMBER, NOVEMBER.end)
    kept = files(place.folder())
    # When
    again = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    # Then
    assert again == first
    assert files(place.folder()) == kept


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
@pytest.mark.parametrize(
    ("customer", "period"),
    [
        (HIKARI.name, NOVEMBER),
        (MINATO_TOKYO.name, NOVEMBER),
        ("株式会社みなと", NOVEMBER),
        (MINATO.name, OCTOBER),
        (MINATO.name, Period(date(2026, 10, 21), date(2026, 11, 20))),
        (MINATO.name, Period(date(2026, 11, 1), date(2026, 11, 29))),
    ],
)
def test_取引先か期間が違えば近い組にもほかの組に付けていない番号を付ける(
    home: Path, customer: str, period: Period
) -> None:
    # Given: みなと商事の 11 月分に番号を付けた状態。
    first = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    # When
    other = numbering.number(customer, period, period.end)
    # Then
    assert other != first
    assert numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end) == first


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行記録が壊れていれば壊れていると断り発行記録を前のまま残す(home: Path) -> None:
    # Given: 発行記録が壊れた状態。
    numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    for each in files(place.folder()):
        each.write_bytes(b"\x00broken")
    kept = files(place.folder())
    # When
    with pytest.raises(place.StoreRefused) as refused:
        numbering.number(MINATO.name, OCTOBER, OCTOBER.end)
    # Then
    assert refused.value.fix.problem == "broken"
    assert refused.value.fix.path in kept
    assert files(place.folder()) == kept


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
@pytest.mark.parametrize("content", ['"2026-11-001"', "1"])
def test_発行記録が読めても発行記録の形に合わなければ壊れていると断り前のまま残す(home: Path, content: str) -> None:
    # Given: 発行記録のファイルが、JSON としては読めるが、組と番号を持たない状態。
    numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    for each in files(place.folder()):
        each.write_text(content, encoding="utf-8")
    kept = files(place.folder())
    # When
    with pytest.raises(place.StoreRefused) as refused:
        numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    # Then
    assert refused.value.fix.problem == "broken"
    assert refused.value.fix.path in kept
    assert files(place.folder()) == kept


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
def test_書けない発行記録では前に付けた組には番号を返し初めての組は書けないと断る(home: Path) -> None:
    # Given: 一つの組に番号を付けたあと、置き場に書けなくなった状態。
    if os.geteuid() == 0:
        pytest.skip("root はどこにでも書ける")
    first = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    kept = files(place.folder())
    locked = [place.folder(), *place.folder().rglob("*")]
    for each in locked:
        each.chmod(0o500 if each.is_dir() else 0o400)
    try:
        # When
        again = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
        with pytest.raises(place.StoreRefused) as refused:
            numbering.number(MINATO.name, OCTOBER, OCTOBER.end)
        # Then
        assert again == first
        assert refused.value.fix.problem == "unwritable"
        assert files(place.folder()) == kept
    finally:
        for each in locked:
            each.chmod(0o700 if each.is_dir() else 0o600)
```

`invoice/tests/unit/test_layout.py` は、`layout.typeset` を確かめる。

```python
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
from tests.given import HIKARI, README_INVOICE, README_PAPER, pages, paper, row

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
    for line in README_PAPER:
        assert line in paper(document)
    assert "10%(軽減税率)" not in paper(document)
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
    assert "株式会社ひかり設計 御中" in paper(documents[0]) and "請求書番号: A-1" in paper(documents[0])
    assert "株式会社みなと商事 御中" in paper(documents[1])
    assert "山田 太郎 様" in paper(documents[2]) and "請求書番号: A-3" in paper(documents[2])


@supports("test_税込の単価の明細では税込の合計から消費税額が出る")
def test_税込の請求書は単価と金額と対象額を税込と示す() -> None:
    # Given
    invoice = replaced(tax_included=True)
    # When
    [document] = layout.typeset([invoice])
    # Then
    text = paper(document)
    assert "取引日 品目 数量 単価(税込) 税率 金額(税込)" in text
    assert "税率 対象額(税込) 消費税額" in text
    assert "税抜" not in text


@supports("test_画面と紙面の金額は請求の計算が決めた額と同じ")
def test_額は請求書のものをそのまま載せ計算し直さない() -> None:
    # Given: 明細と合わない額を持つ請求書。
    invoice = replaced(amount=99999, totals=(RateTotal(10, 1, 2), RateTotal(8, 3, 4)))
    # When
    [document] = layout.typeset([invoice])
    # Then
    text = paper(document)
    assert "ご請求金額(税込): 99,999 円" in text
    assert "合計(税込): 99,999 円" in text
    assert "10% 1 2" in text
    assert "8%(軽減税率) 3 4" in text


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_単位の空の行は数量だけを載せる() -> None:
    # Given
    line = InvoiceLine(row(2, date(2026, 11, 5), "コピー用紙 A4 500枚", 10, "", 2800, 10), 28000)
    invoice = replaced(lines=(line,))
    # When
    [document] = layout.typeset([invoice])
    # Then
    assert "2026年11月5日 コピー用紙 A4 500枚 10 2,800 10% 28,000" in paper(document)


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
@pytest.mark.parametrize("count", [1, 80])
def test_用紙の枚数は紙面のページの数ですべての行を載せる(count: int) -> None:
    # Given: 一行か、八十行の明細の請求書。
    lines = tuple(
        InvoiceLine(row(2 + i, date(2026, 11, 1 + i % 30), f"品目 {i:03}", 1, "個", 100, 10), 100)
        for i in range(count)
    )
    invoice = replaced(lines=lines)
    # When
    [document] = layout.typeset([invoice])
    # Then
    assert document.sheets == pages(document) >= 1
    for i in range(count):
        assert f"品目 {i:03}" in paper(document)
```

`invoice/tests/unit/test_printing.py` は、`printing.print_documents` と `printing.send` を確かめる。

```python
"""印刷 (printing.print_documents, printing.send) の単体ケース。"""

from __future__ import annotations

import pytest

from invoice import layout, printing
from invoice.layout import PrintDocument
from invoice.printing import Printed
from tests.given import README_INVOICE, Printer

supports = pytest.mark.supports


def documents(*sheets: int) -> list[PrintDocument]:
    return [PrintDocument(pdf=b"%PDF-" + bytes([i]), sheets=count) for i, count in enumerate(sheets)]


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
@pytest.mark.parametrize("sheets", [(1,), (2,), (1, 3, 1)])
def test_紙面を受け取った順に送り既定のプリンターの名前と送った用紙の枚数を返す(
    printer: Printer, sheets: tuple[int, ...]
) -> None:
    # Given: 一枚か二枚の紙面が一つ、またはいくつかの紙面。明細には一行以上あるので、紙面は一つ以上ある。
    #   既定のプリンターの名前は、ガイドの例と違う「2階の複合機」。
    printer.name = "2階の複合機"
    given = documents(*sheets)
    # When
    sent = printing.print_documents(given)
    # Then
    assert sent == Printed(printer="2階の複合機", sheets=sum(sheets))
    assert printer.sent == given


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
def test_既定のプリンターがなければ一つも送らずに断る(printer: Printer) -> None:
    # Given
    printer.refuse_at, printer.problem = 0, "no_default_printer"
    # When
    with pytest.raises(printing.PrintRefused) as refused:
        printing.print_documents(documents(1, 1))
    # Then
    assert refused.value.fix.problem == "no_default_printer"
    assert printer.sent == []


@supports("test_送る途中で送れなくなると整え方を示して止まる")
def test_途中で送れなくなればそこで断りあとの紙面は送らない(printer: Printer) -> None:
    # Given
    printer.refuse_at = 1
    given = documents(1, 2, 1)
    # When
    with pytest.raises(printing.PrintRefused) as refused:
        printing.print_documents(given)
    # Then
    assert refused.value.fix.problem == "send_failed"
    assert printer.sent == given[:1]


@pytest.mark.host
@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_本物の印刷システムは既定のプリンターへの印刷を受け付ける() -> None:
    # Given: 既定のプリンターのある印刷システムと、ガイドの請求書の紙面。
    [document] = layout.typeset([README_INVOICE])
    # When
    name = printing.send(document)
    # Then: 印刷システムが断らずに受け付け、PrintRefused が上がらず、既定のプリンターの名前を返す。
    assert name != ""
```

## プロパティ

プロパティは、要件だけから取った決まりを、使い方がもたらすどの入力にも確かめる。

各プロパティは、Hughes の種類と、拠る要素を名指しする。

`invoice/tests/unit/test_properties.py` は、Hypothesis で入力を作る。

```python
"""invoice の要件から取った、使い方がもたらすどの入力にも成り立つ決まりのプロパティ。"""

from __future__ import annotations

import calendar
import dataclasses
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
from invoice.ledger import LedgerRow
from invoice.periods import Dates, Period
from tests.given import AOBA, COLUMNS, HIKARI, ITEMS, MINATO, MINATO_TOKYO, README_ROWS, csv, fresh_home

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


CUSTOMERS = (MINATO, MINATO_TOKYO, HIKARI)
"""明細の取引先。名前の似た二つを含む。"""


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


def amounts(invoices: Sequence[Invoice]) -> dict[tuple[str, Period], tuple[int, frozenset[object]]]:
    """取引先と期間ごとの、請求額と税率ごとの合計。並びの順によらない。"""
    return {(each.customer.name, each.period): (each.amount, frozenset(each.totals)) for each in invoices}


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
def test_形どおりで範囲に入る支払条件だけが三つの値に読み取られる(
    closing: Day, month: int, payment: Day
) -> None:
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
    issuer_info = dataclasses.replace(AOBA, payment_terms=terms)
    # When
    with fresh_home():
        invoices = billing.bill(rows, issuer_info)
    # Then
    assert len(invoices) == len(summary(invoices))
    assert summary(invoices) == model_bill(rows, terms)


@supports("P3.4", "明細行")
@given(rows=ledger_rows(), seed=st.integers())
def test_明細の行の順を入れ替えても取引先と期間ごとの額は変わらない(
    rows: tuple[LedgerRow, ...], seed: int
) -> None:
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
def test_同じ組には同じ番号を別の組には発行月ごとの次の番号を付ける(requests: list[tuple[str, Period]]) -> None:
    """モデルに基づくプロパティ。モデルは、組から初めに付けた番号への辞書と、発行月ごとに付けた数。"""
    # Given any: 取引先と締めの期間の組を、繰り返しも含めて並べた求め。発行日は締めの期間の締め日 (P3.6)。
    # When
    with fresh_home():
        numbers = [numbering.number(customer, period, period.end) for customer, period in requests]
    # Then
    first: dict[tuple[str, Period], str] = {}
    counted: dict[tuple[int, int], int] = {}
    for (customer, period), number in zip(requests, numbers, strict=True):
        if (customer, period) not in first:
            month = (period.end.year, period.end.month)
            counted[month] = counted.get(month, 0) + 1
            first[(customer, period)] = f"{month[0]}-{month[1]:02}-{counted[month]:03}"
        assert number == first[(customer, period)]
    assert len(set(first.values())) == len(first)


REFUSED = {"取引日": "2026-11-31", "数量": "十", "単価(税抜)": "二千八百", "税率": "5%"}
"""明細の列ごとの、受け付けない値。"""


@supports("P1.3", "直すところ")
@given(data=st.data())
def test_明細の誤りはすべての行を読んでから一度に示される(data: st.DataObject) -> None:
    """モデルに基づくプロパティ。モデルは、誤りを入れた行と列の集まり。"""
    # Given any: 何行かの明細と、そのどこかの列に入れた、受け付けない値。
    count = data.draw(st.integers(1, 30))
    broken = data.draw(
        st.sets(st.tuples(st.integers(0, count - 1), st.sampled_from(tuple(REFUSED))), min_size=1)
    )
    rows = []
    for i in range(count):
        cells = README_ROWS[0].split(",")
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
"""読み替える全角の英数字と記号、半角カナ。読み替えは test_ledger.py と test_issuer.py が確かめる。"""
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
```

## トレース

トレースは、`invoice/tests/trace.py` が確かめる。

リポジトリの一番上で `python3 invoice/tests/trace.py check invoice` と打つと、不備がなければ 0 を返す。

ケースは、`invoice` のフォルダーで `uv run pytest` と打って走らせる。

本物の印刷システムを動かすケースは、`--host` を足したときだけ走る。

```python
"""invoice のトレースを確かめる。

    python3 invoice/tests/trace.py check <invoice の一式のフォルダー>

アーキテクチャの要素ごとに結合ケースがあり、どのケースも一つ上の段の要素かケースを
名指ししているかを確かめる。不備がなければ 0、あれば不備を一行ずつ示して 1、
引数が違えば使い方を示して 2 を返す。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

USAGE = "usage: trace.py check <product>\n"


def section(text: str, heading: str) -> str:
    """見出しから、同じか上の段の次の見出しまで。"""
    level = heading.split()[0]
    start = text.index(f"\n{heading}\n")
    rest = text[start + len(heading) + 2 :]
    end = re.search(rf"^#{{1,{len(level)}}} ", rest, re.M)
    return rest[: end.start()] if end else rest


def elements(product: Path) -> tuple[set[str], set[str]]:
    """鍵となる結果の ID と、アーキテクチャの要素の名前。"""
    vision = (product / "docs" / "product-vision.md").read_text(encoding="utf-8")
    architecture = (product / "docs" / "architecture.md").read_text(encoding="utf-8")
    results = set(re.findall(r"^\s*- (KR\d+\.\d+):", vision, re.M))
    stories = set(re.findall(r"^- (S\d+):", architecture, re.M))
    principles = set(re.findall(r"^\s+- (P\d+\.\d+):", architecture, re.M))
    # データの名前は句読点を持たず、方針の行はその決まりの原則の項目で名指される。
    data = set(re.findall(r"^- ([^\s、。\[\]]+)\\$", section(architecture, "### データモデル"), re.M))
    components = set(re.findall(r"^- (\S+) \(", section(architecture, "### コンポーネント"), re.M))
    return results, stories | principles | data | components


def cases(folder: Path) -> dict[str, tuple[Path, tuple[str, ...], bool]]:
    """フォルダーの各テストを、名前から、ファイル、名指すもの、プロパティかどうかへ。"""
    found = {}
    for path in sorted(folder.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            names: tuple[str, ...] = ()
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name | ast.Attribute)
                    and (getattr(decorator.func, "id", None) or getattr(decorator.func, "attr", None)) == "supports"
                ):
                    names += tuple(str(arg.value) for arg in decorator.args if isinstance(arg, ast.Constant))
            found[node.name] = (path, names, path.name == "test_properties.py")
    return found


def faults(product: Path) -> list[str]:
    """トレースの不備を、一行ずつ。"""
    results, architecture = elements(product)
    tests = product / "tests"
    e2e, integration, unit = (cases(tests / level) for level in ("e2e", "integration", "unit"))
    found = []
    for level, named, allowed in (
        ("e2e", e2e, results),
        ("integration", integration, architecture),
    ):
        for name, (path, names, _) in named.items():
            if not names:
                found.append(f"{path}: {name}: 何も名指ししていない")
            for each in names:
                if each not in allowed:
                    found.append(f"{path}: {name}: {each} は {level} の一つ上の段にない")
    for name, (path, names, property_) in unit.items():
        allowed = architecture if property_ else set(integration)
        if not names:
            found.append(f"{path}: {name}: 何も名指ししていない")
        for each in names:
            if each not in allowed:
                found.append(f"{path}: {name}: {each} は一つ上の段にない")
    reached = {each for _, names, _ in integration.values() for each in names}
    found += [f"{tests / 'integration'}: {each} を名指す結合ケースがない" for each in sorted(architecture - reached)]
    covered = {each for _, names, _ in e2e.values() for each in names}
    found += [f"{tests / 'e2e'}: {each} を名指す E2E ケースがない" for each in sorted(results - covered)]
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "check":
        sys.stderr.write(USAGE)
        return 2
    found = faults(Path(argv[1]))
    for each in found:
        print(each)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

## ギャップ

- 請求書の組版: `invoice/templates/invoice.md.j2` が読む値の名前が、`billing.Invoice` と合わない。テンプレートは `invoice.total`、`line.item`、`line.reduced`、`invoice.tax_summaries` を読む。間を運ぶインターフェースがなく、ケースはテンプレートを通した紙面を確かめられない。
- 請求書の組版: テンプレートは Markdown を描くが、`layout.typeset` は PDF を返す。Markdown を PDF にする部品がなく、ケースはその間を確かめられない。
- S1 の「番号を求める (請求書)」: この矢印は請求書を運ぶが、`numbering.number` は取引先の名称と締めの期間と発行日を受け取る。ケースはスケルトンの三つの値で書き、矢印のデータとは合わない。
- S1 と S4 の「送った枚数を返す」と P2.6: 矢印と原則に既定のプリンターの名前がないが、`printing.print_documents` と `command.main` の契約は名前も示す。ケースはガイドと契約のとおりに名前を確かめ、矢印と原則とは合わない。
- S3 の「ないと返す」: この矢印にデータがないが、`issuer.load` は尋ねる事柄を返す。ケースは返った事柄のとおりに尋ねることを確かめ、矢印とは合わない。
- 請求書の組版: 紙面の取引日の形が、契約とガイドで違う。`layout.typeset` の契約は「2026年11月5日」の形で載せる。ガイドの「使ってみる」の紙面は「2026/11/05」と示す。ケースは契約の形で書き、ガイドの形は確かめない。
- 請求の計算: `billing.bill` が返す請求書の順と、`totals` の税率の順が決まっていない。同じ発行月のどの請求書が 001 になるかも、この順で決まる。ケースは順によらずに比べ、番号は発行月ごとの番号の集まりで確かめる。紙面の税率の行の順も確かめない。
- 明細の読み取り: 単価の `2,800` のような桁区切りを受け付けるかが決まっておらず、ケースを書けない。
- 明細の読み取り: 見出しの列の順の違い、余分な列、空のファイルも決まっていない。空の行、すべての列が空の行、品目の空の行も同じで、ケースを書けない。
- 明細の読み取り: 取引先の名称の「法人格」に、`(株)` のような略した書き方が入るかが決まっていない。`ledger.read` の敬称のケースは、略さない法人格と、法人格のない名称でだけ書いた。
- 発行者情報の保管: 答えの前後の空白を受け付けるかが決まっていない。日本語の入力で起きやすいが、`issuer.check` のケースを書けない。
- コマンド: 直すところの文言は契約になく、ケースは行と列と値と例が示されることだけを確かめる。読めない明細では、UTF-8 の CSV で保存し直す手順の文言もなく、ケースはパスと `UTF-8` と `CSV` の語が示されることだけを確かめる。
- コマンド: 尋ねる途中で利用者が `Ctrl` + `D` を押して入力が尽きたときの終わり方が決まっておらず、ケースを書けない。本体にその分かれ道があれば、単体ケースだけでは分岐網羅の 100% に届かない。
- コマンド: 端末でない入力から答えを受けたときに、答えを画面に示し直すかが決まっておらず、ケースを書けない。
- 印刷: `printing.send` が印刷システムにどう頼むかが決まっておらず、契約テストの手順を書けない。
- 印刷: 途中で送れなくなったあとの打ち直しで、送れた紙面をまた送るかが決まっていない。ケースは打ち直しの枚数を確かめられない。
- 発行者情報の保管と番号の採番: 残すファイルの形が決まっておらず、データ互換性テストの前の版のファイルを作れない。
- S1 と S3: 置き場のファイルを読めないか残せないときの分かれ道がない。ケースは `place.StoreRefused` のとおりに書き、S1 と S3 を名指しした。
- S2 の「配布物がまだない」: この分かれ道は uv とリリースの置き場の間だけにあり、持つ部品が invoice にない。空の本体でも通るケースしか書けず、結合ケースを置かない。
- ディレクトリ構成: トレースを確かめるスクリプトの置き場がなく、`invoice/tests/trace.py` に置いた。
