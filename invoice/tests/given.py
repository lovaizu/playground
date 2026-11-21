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

HEADER = "取引先,取引日,品目,数量,単位,単価(税抜),税率"
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

明細の取引日は、invoice/templates/ のテンプレートのとおり年月日で載る。
"""


def save_aoba(**changed: str) -> Issuer:
    """ガイドの答えを、changed の事柄だけ替えて確かめさせ、発行者情報として残させる。"""
    answers = dict(zip(ITEMS, AOBA_ANSWERS, strict=True)) | changed
    return issuer.save({item: issuer.check(item, answers[item]) for item in ITEMS})


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
