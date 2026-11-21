# スケルトン

## モジュールの冒頭

各モジュールは、自分だけが隠す一つの決めごとを、ファイルの冒頭の docstring に書く。

- `src/invoice/command.py`: 部品の結果と直すところを、利用者に端末でどう示すか。
- `src/invoice/ledger.py`: 明細のファイルを、どの形なら受け付け、各列をどう読んで明細行にするか。
- `src/invoice/place.py`: invoice が残すファイルを、ノートPCのどこに置くか。
- `src/invoice/issuer.py`: 発行者情報の形を、尋ねる事柄とその順と名前から、残すファイルの中身まで決める。
- `src/invoice/billing.py`: 請求書の額を、消費税と合計の決まりに沿ってどう出すか。
- `src/invoice/periods.py`: 取引日と支払条件から、締めの期間と発行日と支払期限をどう決めるか。
- `src/invoice/numbering.py`: 取引先と締めの期間の組に、どの請求書番号を付けるか。
- `src/invoice/layout.py`: 請求書を、用紙の上にどう配置するか。
- `src/invoice/printing.py`: 紙面を、ノートPCの印刷システムにどう届けるか。

請求の計算のコンポーネントは、billing.py と periods.py の二つのモジュールに分ける。
消費税の決まりと、締めの期間と支払期限の決まりは、別のわけで変わるからである。
置き場の場所は place.py だけが決め、issuer.py と numbering.py はそこから受け取る。
初回に尋ねる発行者の事柄と、その順と名前は、issuer.py だけが決める。
command.py は、受け取った事柄を受け取った順に尋ねるだけである。
取引先の敬称は、明細の「取引先」の列の読み方として ledger.py が決める。
S2 のインストーラーは uv であり、invoice のコードではない。
S2 で invoice のコードに届く矢印は、版を尋ねる `invoice --version` だけである。

## インターフェース

各インターフェースは、シーケンスの矢印を一つずつ運ぶ。
本体は呼ぶと失敗し、そのインターフェースの名前を示す。
型は Python の注釈で書き、契約は docstring に書く。

`pyproject.toml` のコマンドの入口は、`command.main` を呼ぶ。

```toml
[project.scripts]
invoice = "invoice.command:main"
```

`src/invoice/command.py` は、利用者からの矢印を受ける。

```python
"""部品の結果と直すところを、利用者に端末でどう示すか。"""

from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """明細のファイルを渡す (S1, S3, S4)、版を尋ねる (S2)。

    受け取る: コマンドラインの引数。明細のファイルのパス一つか、`--version`。
        None のときは sys.argv[1:] を使う。
    返す: 終了コード。
        0: 印刷を頼み終え、請求書ごとの番号と金額と、送った既定のプリンターの名前と、
           印刷した枚数を示した (P2.6)。
           `--version` では版を示した (S2)。
        1: 直すところを示して止まった (P1.2)。
        2: 引数が明細のファイル一つでも `--version` でもなく、使い方を示した。
        130: 発行者情報を尋ねる途中で、利用者が答えずに止めた (P2.4)。
    ほかに変えるもの:
        端末で尋ね、示す。利用者と言葉を交わすのは、このモジュールだけ (P1.2)。
        明細に直すところがないときにだけ、発行者情報を求め、印刷に進む (P2.5)。
        発行者情報がないときは、issuer.load が返した事柄を、受け取った順に、
        その名前と例のとおりに尋ねるだけ。何をどの順に尋ねるかは決めない。
        初回は、すべての答えがそろったときにだけ発行者情報を残させる (P2.4)。
        番号の採番を通して発行記録を、印刷を通して既定のプリンターを動かす。
    断るとき:
        ledger.LedgerRefused: すべての直すところを、その problem ごとに示し、
            何も尋ねず、何も印刷せずに 1 を返す (P1.3, P2.5)。
            not_found: そのパスにファイルがないことと、パスの確かめ方を示す。
            unreadable: そのファイルを読めないことと、UTF-8 の CSV での保存し直し方を示す。
            no_rows: 明細に行が一つもないことと、一行の例を示す。
            bad_value: 行と列と書かれていた値と、受け付ける形の例を示す。
        issuer.AnswerRefused: 受け付ける形の例を示し、同じ事柄を尋ね直す (P1.5)。
        place.StoreRefused: どのファイルの何が問題かと直し方を示し、
            何も印刷せずに 1 を返す。
        printing.PrintRefused: プリンターの整え方を示して 1 を返す (S4)。
    """
    raise NotImplementedError("command.main")
```

`src/invoice/ledger.py` は、明細を読ませる矢印を受ける。

```python
"""明細のファイルを、どの形なら受け付け、各列をどう読んで明細行にするか。"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

TaxRate = Literal[8, 10]
"""明細行の消費税率 (%)。8 は軽減税率で、請求書にその旨を載せる。"""


@dataclass(frozen=True)
class Customer:
    """取引先: 請求書の宛先。"""

    name: str
    """取引先の正式な名称。明細の「取引先」の列のまま。"""
    honorific: Literal["御中", "様"]
    """宛名の敬称。名称に法人格があれば「御中」、なければ「様」。
    例: `株式会社青葉商事` は「御中」、`山田太郎` は「様」。
    明細の「取引先」の列の名称から、このモジュールが読み取る。"""


@dataclass(frozen=True)
class LedgerRow:
    """明細行: 一つの取引を表し、請求書の明細の一行になる。"""

    line: int
    """明細のファイルでの行の番号。1 から数える。"""
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
    """誤りの列の見出し。problem が bad_value でなければ None。"""
    given: str | None
    """明細に書かれていた値。値がない、または problem が bad_value でなければ None。"""
    expected: str
    """受け付ける形の例。bad_value では値の例。例: `2026-11-20`。
    no_rows では明細の一行の例。not_found と unreadable では空。"""
    detail: str
    """ファイルシステムか CSV の読み取りが返したわけ。なければ空。"""


class LedgerRefused(Exception):
    """明細を請求書にできないときに上がり、すべての直すところを持つ。"""

    def __init__(self, fixes: tuple[LedgerFix, ...]) -> None:
        super().__init__(fixes)
        self.fixes = fixes


def read(path: Path) -> tuple[LedgerRow, ...]:
    """明細を読ませる (S1, S3, S4)。

    受け取る: 明細のファイルのパス。見出しは、取引先、取引日、品目、数量、単位、
        `単価(税抜)` か `単価(税込)`、税率の七つの列。
    返す: 明細のすべての行を、ファイルの順に明細行として。一行以上。
        各値は、全角の数字・英字・記号を半角に、半角カナを全角に読み替えてから確かめ、
        読み替えた値を明細行に持つ。
        取引日は `2026-11-05` か `2026/11/05` の形を、数量と単価は正の整数を、
        税率は `10%` か `8%` を受け付ける。
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
                すべての行を読み終えてから、すべての直すところを持って上がる (P1.3)。
    """
    raise NotImplementedError("ledger.read")
```

`src/invoice/place.py` は、発行者情報の保管と番号の採番が呼ぶ。
置き場の場所と、そこで読み書きできないときの直すところを渡す。

```python
"""invoice が残すファイルを、ノートPCのどこに置くか。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class StoreFix:
    """直すところ: 置き場のファイルの一つを読めない、または残せないわけ。

    コマンドはこの値だけから、どのファイルの何をどう直すかを日本語で示す。
    """

    path: Path
    """問題のファイル。"""
    problem: Literal["unreadable", "broken", "unwritable"]
    """読めない、中身が壊れている、または書けない。"""
    detail: str
    """ファイルシステムか読み取りが返したわけ。なければ空。"""


class StoreRefused(Exception):
    """置き場のファイルを読めない、または残せないときに上がり、直すところを持つ。"""

    def __init__(self, fix: StoreFix) -> None:
        super().__init__(fix)
        self.fix = fix


def folder() -> Path:
    """invoice の置き場のフォルダー。利用者のホームフォルダーの中にある (P2.2)。

    受け取る: なし。
    返す: 置き場のフォルダーのパス。どのフォルダーで打っても同じパス。
    ほかに変えるもの: なし。フォルダーを作るのは、残す側のモジュール。
    断るとき: なし。
    """
    raise NotImplementedError("place.folder")
```

`src/invoice/issuer.py` は、残した情報を求める矢印、答えを確かめさせる矢印、すべての答えを残させる矢印を受ける。

```python
"""発行者情報の形を、尋ねる事柄とその順と名前から、残すファイルの中身まで決める。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypeAlias

IssuerItem: TypeAlias = Literal[
    "name",
    "registration_number",
    "payment_terms",
    "bank_name",
    "bank_branch",
    "account_type",
    "account_number",
    "account_holder",
]
"""発行者情報の事柄。名称、登録番号、支払条件 (P3.1, P3.9) と、
お振込先の銀行名、支店名、口座種別、口座番号、口座名義。"""

Day: TypeAlias = int | Literal["month_end"]
"""締め日か支払日。1 から 28 の日か、月末 (P3.12)。"""


@dataclass(frozen=True)
class PaymentTerms:
    """支払条件を、締め日、支払の月、支払日の三つの値で表す。"""

    closing_day: Day
    """締め日。"""
    month: Literal[0, 1, 2]
    """支払の月。0 は当月、1 は翌月、2 は翌々月。"""
    payment_day: Day
    """支払日。"""


Answer: TypeAlias = str | PaymentTerms
"""確かめ終えた一つの答え。支払条件は PaymentTerms、ほかの事柄は str。"""


@dataclass(frozen=True)
class BankAccount:
    """お振込先: 取引先が請求額を振り込む、発行者の口座。"""

    name: str
    """銀行名。例: `さくら銀行`。"""
    branch: str
    """支店名。例: `本店営業部`。"""
    account_type: Literal["普通", "当座"]
    """口座種別。"""
    account_number: str
    """口座番号。7 桁の数字。"""
    account_holder: str
    """口座名義。カナ。例: `カ)アオバジムヨウヒン`。"""


@dataclass(frozen=True)
class Issuer:
    """発行者情報: 請求書を出す側として毎回載せる事柄と、支払条件。"""

    name: str
    """発行者の名称。"""
    registration_number: str
    """適格請求書発行事業者の登録番号。T と 13 桁の数字。"""
    payment_terms: PaymentTerms
    """支払条件。"""
    bank: BankAccount
    """お振込先。請求書にそのまま載せる。"""


@dataclass(frozen=True)
class Question:
    """尋ねる一つの事柄。コマンドはこの値だけから問いを示す。

    尋ねる事柄、その順、利用者に見せる名前と例を決めるのは、このモジュールだけ。
    """

    item: IssuerItem
    """事柄。"""
    label: str
    """利用者に見せる事柄の名前。例: `登録番号(T と 13 桁の数字)`。"""
    example: str
    """受け付ける形の例。例: `T1234567890123`。"""


@dataclass(frozen=True)
class AnswerFix:
    """直すところ: 形に合わない一つの答えと、受け付ける形の例。"""

    item: IssuerItem
    """答えが形に合わなかった事柄。"""
    given: str
    """利用者の答え。"""
    expected: str
    """受け付ける形の例。例: `20日締め翌月10日払い`。"""


class AnswerRefused(Exception):
    """答えが形に合わないときに上がり、直すところを持つ。"""

    def __init__(self, fix: AnswerFix) -> None:
        super().__init__(fix)
        self.fix = fix


class AnswersIncomplete(Exception):
    """残させた答えに欠けた事柄があるときに上がり、欠けた事柄を持つ。"""

    def __init__(self, missing: tuple[IssuerItem, ...]) -> None:
        super().__init__(missing)
        self.missing = missing


def load() -> Issuer | tuple[Question, ...]:
    """残した情報を求める (S1, S3)。

    受け取る: なし。置き場の場所は place.folder から受け取る。
    返す: 残した発行者情報。
        まだ残していなければ、尋ねる事柄を尋ねる順に (P2.1)。
        名称、登録番号、支払条件、銀行名、支店名、口座種別、口座番号、口座名義の順。
        尋ねる事柄の一覧とその順と名前を持つのは、このモジュールだけ。
    ほかに変えるもの: なし。
    断るとき:
        place.StoreRefused: 発行者情報のファイルが読めない、または壊れているとき。
    """
    raise NotImplementedError("issuer.load")


def check(item: IssuerItem, answer: str) -> Answer:
    """答えを確かめさせる (S3)。

    受け取る: 尋ねた事柄と、利用者の答えの文字列。
    返す: 確かめ終えた答え。支払条件は三つの値に読み取る (P3.10)。
        答えは、全角の数字・英字・記号を半角に、半角カナを全角に読み替えてから確かめ、
        読み替えた値を返す。
    ほかに変えるもの: なし。何も残さない (P2.4)。
    断るとき:
        AnswerRefused: 答えが事柄の形に合わないとき。支払条件では、
            「20日締め翌月10日払い」の形でないとき (P3.10)、
            締め日か支払日が 1 から 28 の日でも月末でもないとき (P3.12)、
            当月払いで支払日が締め日より後でないとき (P3.11)。
            お振込先では、口座種別が「普通」でも「当座」でもないとき、
            口座番号が 7 桁の数字でないとき、口座名義がカナでないとき。
            どの事柄でも、答えが空のとき。
    """
    raise NotImplementedError("issuer.check")


def save(answers: Mapping[IssuerItem, Answer]) -> Issuer:
    """すべての答えを残させる (S3)。

    受け取る: check が返した答えを、事柄ごとに。
    返す: 残した発行者情報。
    ほかに変えるもの: 発行者情報を、place.folder の中に、すべて一度に残す (P2.4)。
    断るとき:
        AnswersIncomplete: 欠けた事柄があるとき。何も残さない (P2.4)。
        place.StoreRefused: 発行者情報のファイルを書けないとき。何も残さない (P2.4)。
    """
    raise NotImplementedError("issuer.save")
```

`src/invoice/periods.py` は、請求の計算のコンポーネントの中で billing.py が呼ぶ。

```python
"""取引日と支払条件から、締めの期間と発行日と支払期限をどう決めるか。"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from invoice.issuer import PaymentTerms


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
        同じ期間に入る取引日には、同じ値を返す。
    ほかに変えるもの: なし。
    断るとき: なし。支払条件は issuer.check が確かめ終えている。
    """
    raise NotImplementedError("periods.dates_of")
```

`src/invoice/billing.py` は、請求書にさせる矢印を受ける。

```python
"""請求書の額を、消費税と合計の決まりに沿ってどう出すか。"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

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
    """明細に載せる行と金額。取引日が締めの期間に入る明細行を (P3.8)、
    取引日の順に並べ、同じ取引日の行は明細のファイルの順に保つ。"""
    totals: tuple[RateTotal, ...]
    """税率ごとの合計。一つ以上。"""
    amount: int
    """請求額。税込の円の整数。ご請求金額と合計(税込)に載せる。"""


def bill(rows: Sequence[LedgerRow], issuer: Issuer) -> tuple[Invoice, ...]:
    """請求書にさせる (S1)。

    受け取る: 直すところのない明細行と、発行者情報。
    返す: 取引先と締めの期間ごとに一枚ずつの請求書 (P3.4)。
        日付は periods.dates_of に求め、番号は numbering.number に、
        取引先の名称と、dates_of が返した締めの期間と発行日を渡して求める。
        各行の金額、税率ごとの対象額と消費税額、請求額を決めるのは、
        このモジュールだけ (P3.1)。
    ほかに変えるもの: 番号の採番を通して、発行記録に番号を残させる。
    断るとき:
        place.StoreRefused: numbering.number が断ったとき、そのまま上げる。
    """
    raise NotImplementedError("billing.bill")
```

`src/invoice/numbering.py` は、番号を求める矢印を受ける。

```python
"""取引先と締めの期間の組に、どの請求書番号を付けるか。"""

from __future__ import annotations

import datetime

from invoice.periods import Period


def number(customer_name: str, period: Period, issue_date: datetime.date) -> str:
    """番号を求める (S1)。

    受け取る: 請求書の取引先の名称と締めの期間と、periods.dates_of が決めた発行日。
        置き場の場所は place.folder から受け取る。
    返す: その組の請求書番号。前に付けた組には、前と同じ番号 (P3.5, P1.4)。
        初めての組には、ほかの組に付けていない番号。
        番号は「<発行年>-<発行月2桁>-<連番3桁>」の形で、例: `2026-11-001`。
        連番は発行日の月ごとに 001 から数え、その月に付けた番号の次とする。
    ほかに変えるもの: 初めての組なら、その番号を発行記録に残してから返す。
        発行記録を読み書きするのは、このモジュールだけ (P3.5)。
    断るとき:
        place.StoreRefused: 発行記録のファイルが読めない、壊れている、
            または書けないとき。発行記録は前のまま残す。
    """
    raise NotImplementedError("numbering.number")
```

`src/invoice/layout.py` は、紙面にさせる矢印を受ける。

```python
"""請求書を、用紙の上にどう配置するか。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from invoice.billing import Invoice


@dataclass(frozen=True)
class PrintDocument:
    """印刷用の文書: 一枚の請求書を用紙の上に配置し、プリンターへそのまま渡せるもの。"""

    pdf: bytes
    """紙面の PDF。書体は invoice とともに配るものを埋め込む。"""
    sheets: int
    """用紙の枚数。一以上。"""


def typeset(invoices: Sequence[Invoice]) -> tuple[PrintDocument, ...]:
    """紙面にさせる (S1)。

    受け取る: 請求書。紙面に載せる値は、すべて請求書の中にある。
        宛先: customer.name と customer.honorific。
        発行者: issuer.name、issuer.registration_number、
            お振込先の issuer.bank の name、branch、account_type、
            account_number、account_holder。
        請求書番号と日付: number、issue_date、due_date。
        明細: 各 lines の row の date、description、quantity、unit、unit_price、
            tax_rate と、その行の amount を、lines の順に。
            date は「2026年11月5日」の形で載せる。単価と金額の税込か税抜は tax_included。
            tax_rate が 8 の行には、軽減税率の旨を添える。
        税率ごとの合計: 各 totals の rate、base、tax。
        ご請求金額と合計(税込): amount。
    返す: 請求書ごとに一つの印刷用の文書を、受け取った順に。
        額は請求書のものをそのまま載せ、計算しない (P3.1)。
    ほかに変えるもの: なし。
    断るとき: なし。
    """
    raise NotImplementedError("layout.typeset")
```

`src/invoice/printing.py` は、印刷させる矢印を受け、印刷システムへの矢印を送る。

```python
"""紙面を、ノートPCの印刷システムにどう届けるか。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from invoice.layout import PrintDocument


@dataclass(frozen=True)
class PrintFix:
    """直すところ: 紙面が既定のプリンターに届かないわけ (S4)。"""

    problem: Literal["no_default_printer", "send_failed"]
    """既定のプリンターがない、または送れない。"""
    detail: str
    """印刷システムが返したわけ。なければ空。"""


class PrintRefused(Exception):
    """紙面を既定のプリンターに届けられないときに上がり、直すところを持つ。"""

    def __init__(self, fix: PrintFix) -> None:
        super().__init__(fix)
        self.fix = fix


@dataclass(frozen=True)
class Printed:
    """印刷を頼み終えた結果: 送った先と、送った枚数 (P2.6)。"""

    printer: str
    """送った既定のプリンターの名前。印刷システムが示すまま。"""
    sheets: int
    """送った用紙の枚数。"""


def print_documents(documents: Sequence[PrintDocument]) -> Printed:
    """印刷させる (S1, S4)。

    受け取る: 印刷用の文書。
    返す: 送った既定のプリンターの名前と、送った用紙の枚数 (P2.6)。
        名前は send が返したもの。
    ほかに変えるもの: 文書を受け取った順に、send で既定のプリンターに送る。
    断るとき:
        PrintRefused: 既定のプリンターがないとき、一つも送らずに上がる。
            途中で送れなくなったとき、そこで上がる (S4)。
    """
    raise NotImplementedError("printing.print_documents")


def send(document: PrintDocument) -> str:
    """既定のプリンターに送る (S1, S4)。印刷システムへの矢印を運ぶ。

    印刷システムに触れるのは、この関数だけ (P2.3)。テストでは代役に替える。
    受け取る: 一つの印刷用の文書。
    返す: 送った既定のプリンターの名前。
    ほかに変えるもの: 印刷システムに、既定のプリンターでの印刷を頼む。
    断るとき:
        PrintRefused: 既定のプリンターがないとき、または印刷システムが断ったとき。
    """
    raise NotImplementedError("printing.send")
```

## ギャップ

- ディレクトリ構成: `periods.py` と `place.py` がない。請求の計算の二つのモジュールと置き場の場所の決めごとを、構成と方針に足す必要がある。
- コンポーネント: `place.py` が決める置き場の場所を受け持つコンポーネントがない。どのコンポーネントの決めごとかを、コンポーネントに足す必要がある。
- S3 の「ないと返す」: この矢印にデータがない。`issuer.load` は尋ねる事柄を返すので、矢印に尋ねる事柄を足す必要がある。
- S1 と S3: 発行者情報や発行記録を読めない、または残せないときの分かれ道がない。インターフェースは `place.StoreRefused` で断るので、その分かれ道を足す必要がある。
- S1 と S4 の「送った枚数を返す」: この矢印に既定のプリンターの名前がない。`printing.print_documents` は名前と枚数を返し、コマンドはその名前も示すので、矢印と P2.6 に名前を足す必要がある。
- S1 の「番号を求める」: この矢印は請求書を運ぶが、`numbering.number` は請求書ではなく、取引先の名称と締めの期間と発行日を受け取る。番号は発行月ごとの連番で、請求書の額は要らないので、矢印のデータをこの三つに改める必要がある。
- コンポーネントの図の請求の計算から番号の採番への「番号を求める」: この矢印も、S1 の矢印と同じく請求書を運ぶ。`numbering.number` は取引先の名称と締めの期間と発行日を受け取るので、図の矢印のデータもこの三つに改める必要がある。
- コンポーネントの図の「印刷させる」: 印刷への矢印が返すものに、既定のプリンターの名前がない。`printing.print_documents` は名前と枚数を返すので、図にも名前を足す必要がある。
- コンポーネントの図の「求める、確かめさせる、残させる」: この矢印が返すものに、尋ねる事柄がない。`issuer.load` は発行者情報がまだなければ尋ねる事柄を返すので、図にも足す必要がある。
