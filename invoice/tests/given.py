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


FIRST_TIME = "はじめて使うので、発行者の情報を伺います。次からは聞きません。\n"
"""初回に、事柄を尋ねる前に端末に示す行。"""


def prompts(*labels: str) -> str:
    """事柄の名前を、尋ねた順に端末に示した文。代役の端末は、利用者の答えを画面に示さない。"""
    return "".join(f"{label}: " for label in labels)


ASKED = FIRST_TIME + prompts(*AOBA_LABELS) + "\n"
"""初回に、ガイドの事柄を一度ずつ尋ね終えて、行を改めるまでに端末に示す文。"""


def bill_line(name: str, number: str, amount: str) -> str:
    """端末に示す、一枚の請求書の宛名と請求書番号とご請求金額の行。"""
    return f"{name}: 請求書番号 {number}、ご請求金額 {amount} 円\n"


LEDGER_STOPPED = (
    "invoice: 明細を請求書にできませんでした。次のところを直して保存し、同じコマンドを打ち直してください。\n"
    "何も印刷していません。\n"
)
"""明細に直すところがあるとき、直すところより前に端末に示す行。"""


def bad_value(path: Path, line: int, column: str, given: str | None, rule: str, expected: str) -> str:
    """端末に示す、受け付けない一つの値の直し方の行。"""
    said = f"「{given}」は受け付けられません" if given is not None else "値がありません"
    return f"- {path} の {line} 行目、「{column}」の列: {said}。{rule}たとえば「{expected}」と書きます。\n"


DATE_RULE = "取引日は 2026-11-20 か 2026/11/20 の形の、ある日付で書きます。"
QUANTITY_RULE = "数量は、1 以上の整数で書きます。"
RATE_RULE = "税率は 10% か、軽減税率の品目なら 8% と書きます。"


def store_stopped(path: Path) -> str:
    """置き場のファイルで止まったとき、直し方より前に端末に示す行。"""
    return f"invoice: 発行者の情報と請求書番号を残すファイル {path} で止まりました。何も印刷していません。\n"


NO_PRINTER = (
    "invoice: 既定のプリンターが見つからないため、印刷できませんでした。"
    "「設定」の「プリンター」でプリンターを足して既定にし、端末で lpstat -d を打って"
    "名前が出ることを確かめてから、同じコマンドを打ち直してください。請求書番号は変わりません。\n"
)
"""既定のプリンターがないとき、端末に示すプリンターの整え方。"""


def send_failed(detail: str) -> str:
    """既定のプリンターに送れなかったとき、端末に示すプリンターの整え方。"""
    return (
        f"invoice: 既定のプリンターに送れませんでした ({detail})。"
        "プリンターの電源と用紙と接続を確かめてから、同じコマンドを打ち直してください。"
        "すでに出た請求書も、同じ番号でもう一度印刷されます。\n"
    )


def sheet(
    name: str,
    number: str,
    issued: str,
    amount: str,
    due: str,
    lines: tuple[str, ...],
    totals: tuple[str, ...],
    basis: str = "税抜",
) -> str:
    """あおば事務用品の請求書の紙面に載る文字の全体を、paper と同じく空白を一つにつめて。

    見出しの並びは、invoice/templates/invoice.md.j2 のとおり。
    """
    return " ".join(
        (
            "請求書",
            "宛先",
            name,
            "発行者",
            "株式会社あおば事務用品",
            "登録番号: T1234567890123",
            "請求書番号と発行日",
            f"請求書番号: {number}",
            f"発行日: {issued}",
            "ご請求金額とお支払い",
            f"ご請求金額(税込): {amount} 円",
            f"お支払期限: {due}",
            "お振込先: さくら銀行 本店営業部 普通 1234567 カ)アオバジムヨウヒン",
            "明細",
            f"取引日 品目 数量 単価({basis}) 税率 金額({basis})",
            *lines,
            "税率ごとの合計",
            f"税率 対象額({basis}) 消費税額",
            *totals,
            f"合計(税込): {amount} 円",
        )
    )


README_LINES = README_PAPER[10:13]
"""ガイドの請求書の、明細の三つの行。"""

README_TOTALS = README_PAPER[14:16]
"""ガイドの請求書の、税率ごとの合計の二つの行。"""


def sheets(
    name: str,
    number: str,
    issued: str,
    amount: str,
    due: str,
    lines: tuple[str, ...],
    totals: tuple[str, ...],
    basis: str = "税抜",
) -> set[str]:
    """sheet の紙面を、税率ごとの合計の行がどちらの順に並んでも。行の順は契約で決まっていない。"""
    return {
        sheet(name, number, issued, amount, due, lines, totals, basis),
        sheet(name, number, issued, amount, due, lines, totals[::-1], basis),
    }


README_SHEETS = sheets(
    "株式会社みなと商事 御中", "2026-11-001", "2026年11月30日", "51,980", "2026年12月31日", README_LINES, README_TOTALS
)
"""ガイドの「使ってみる」で、プリンターから出る請求書の紙面の全体。"""


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
