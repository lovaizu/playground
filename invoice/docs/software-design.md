# スケルトン

## モジュールの冒頭

各モジュールは、自分だけが隠す一つの決めごとを、ファイルの冒頭の docstring に書く。

- `src/invoice/command.py`: 利用者と端末で交わすやりとりを、何をどの順に尋ねて示すかまで決める。
- `src/invoice/ledger.py`: 明細のファイルのうち、どの形を請求書にできる明細として受け付けるか。
- `src/invoice/issuer.py`: 発行者情報の形を、尋ねる事柄から残すファイルの中身まで決める。
- `src/invoice/billing.py`: 明細行から、取引先と締めの期間ごとの請求書の中身をどう決めるか。
- `src/invoice/numbering.py`: 取引先と締めの期間の組に、どの請求書番号を付けるか。
- `src/invoice/layout.py`: 請求書を、用紙の上にどう配置するか。
- `src/invoice/printing.py`: 紙面を、ノートPCの印刷システムにどう届けるか。

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
"""利用者と端末で交わすやりとりを、何をどの順に尋ねて示すかまで決める。"""

from __future__ import annotations

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """明細のファイルを渡す (S1, S3, S4)、版を尋ねる (S2)。

    受け取る: コマンドラインの引数。明細のファイルのパス一つか、`--version`。
        None のときは sys.argv[1:] を使う。
    返す: 終了コード。
        0: 印刷を頼み終え、請求書ごとの番号と金額と、印刷した枚数を示した (P2.6)。
           `--version` では版を示した (S2)。
        1: 直すところを示して止まった (P1.2)。
        2: 引数が明細のファイル一つでも `--version` でもなく、使い方を示した。
        130: 発行者情報を尋ねる途中で、利用者が答えずに止めた (P2.4)。
    ほかに変えるもの:
        端末で尋ね、示す。利用者と言葉を交わすのは、このモジュールだけ (P1.2)。
        明細に直すところがないときにだけ、発行者情報を求め、印刷に進む (P2.5)。
        初回は、すべての答えがそろったときにだけ発行者情報を残させる (P2.4)。
        番号の採番を通して発行記録を、印刷を通して既定のプリンターを動かす。
    断るとき:
        ledger.LedgerRefused: すべての直すところを行と直し方で示し、何も尋ねず、
            何も印刷せずに 1 を返す (P1.3, P2.5)。
        issuer.AnswerRefused: 受け付ける形の例を示し、同じ事柄を尋ね直す (P1.5)。
        printing.PrintRefused: プリンターの整え方を示して 1 を返す (S4)。
    """
    raise NotImplementedError("command.main")
```

`src/invoice/ledger.py` は、明細を読ませる矢印を受ける。

```python
"""明細のファイルのうち、どの形を請求書にできる明細として受け付けるか。"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

TaxRate = Literal[8, 10]
"""明細行の消費税率 (%)。8 は軽減税率で、請求書にその旨を載せる。"""


@dataclass(frozen=True)
class LedgerRow:
    """明細行: 一つの取引を表し、請求書の明細の一行になる。"""

    line: int
    """明細のファイルでの行の番号。1 から数える。"""
    customer: str
    """取引先の名称。"""
    date: datetime.date
    """取引日。"""
    description: str
    """取引の内容。"""
    quantity: int
    """数量。"""
    unit_price: int
    """単価。円の整数。"""
    tax_rate: TaxRate
    """消費税率。"""
    tax_included: bool
    """単価が税込なら True (P3.3)。"""


@dataclass(frozen=True)
class LedgerFix:
    """直すところ: 明細の一か所の誤りと、受け付ける形の例。

    コマンドはこの値だけから、どの行の何をどう直すかを日本語で示す (P1.2)。
    """

    line: int | None
    """誤りの行の番号。ファイル全体の誤りなら None。"""
    column: str | None
    """誤りの列の見出し。行全体やファイル全体の誤りなら None。"""
    given: str | None
    """明細に書かれていた値。値がないなら None。"""
    expected: str
    """受け付ける形の例。例: `2026-11-20`。"""


class LedgerRefused(Exception):
    """明細を請求書にできないときに上がり、すべての直すところを持つ。"""

    def __init__(self, fixes: tuple[LedgerFix, ...]) -> None:
        super().__init__(fixes)
        self.fixes = fixes


def read(path: Path) -> tuple[LedgerRow, ...]:
    """明細を読ませる (S1, S3, S4)。

    受け取る: 明細のファイルのパス。
    返す: 明細のすべての行を、ファイルの順に明細行として。一行以上。
    ほかに変えるもの: なし。明細のファイルを読むだけで、書かない。
    断るとき:
        LedgerRefused: ファイルを読めない、行が一つもない、または一行でも
            請求書にできない行があるとき。すべての行を読み終えてから、
            すべての直すところを持って上がる (P1.3)。
    """
    raise NotImplementedError("ledger.read")
```

`src/invoice/issuer.py` は、残した情報を求める矢印、答えを確かめさせる矢印、すべての答えを残させる矢印を受ける。

```python
"""発行者情報の形を、尋ねる事柄から残すファイルの中身まで決める。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypeAlias

IssuerItem: TypeAlias = Literal["name", "registration_number", "payment_terms"]
"""発行者情報の事柄。名称、登録番号、支払条件 (P3.1, P3.9)。"""

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
"""確かめ終えた一つの答え。名称と登録番号は str、支払条件は PaymentTerms。"""


@dataclass(frozen=True)
class Issuer:
    """発行者情報: 請求書を出す側として毎回載せる事柄と、支払条件。"""

    name: str
    """発行者の名称。"""
    registration_number: str
    """適格請求書発行事業者の登録番号。T と 13 桁の数字。"""
    payment_terms: PaymentTerms
    """支払条件。"""


@dataclass(frozen=True)
class IssuerFix:
    """直すところ: 形に合わない一つの答えと、受け付ける形の例。"""

    item: IssuerItem
    """答えが形に合わなかった事柄。"""
    given: str
    """利用者の答え。"""
    expected: str
    """受け付ける形の例。例: `20日締め翌月10日払い`。"""


class AnswerRefused(Exception):
    """答えが形に合わないときに上がり、直すところを持つ。"""

    def __init__(self, fix: IssuerFix) -> None:
        super().__init__(fix)
        self.fix = fix


class AnswersIncomplete(Exception):
    """残させた答えに欠けた事柄があるときに上がり、欠けた事柄を持つ。"""

    def __init__(self, missing: tuple[IssuerItem, ...]) -> None:
        super().__init__(missing)
        self.missing = missing


def load() -> Issuer | None:
    """残した情報を求める (S1, S3)。

    受け取る: なし。
    返す: 残した発行者情報。まだ残していなければ None (P2.1)。
    ほかに変えるもの: なし。
    断るとき: なし。読めない場合はギャップに挙げる。
    """
    raise NotImplementedError("issuer.load")


def check(item: IssuerItem, answer: str) -> Answer:
    """答えを確かめさせる (S3)。

    受け取る: 尋ねた事柄と、利用者の答えの文字列。
    返す: 確かめ終えた答え。支払条件は三つの値に読み取る (P3.10)。
    ほかに変えるもの: なし。何も残さない (P2.4)。
    断るとき:
        AnswerRefused: 答えが事柄の形に合わないとき。支払条件では、
            「20日締め翌月10日払い」の形でないとき (P3.10)、
            締め日か支払日が 1 から 28 の日でも月末でもないとき (P3.12)、
            当月払いで支払日が締め日より後でないとき (P3.11)。
    """
    raise NotImplementedError("issuer.check")


def save(answers: Mapping[IssuerItem, Answer]) -> Issuer:
    """すべての答えを残させる (S3)。

    受け取る: check が返した答えを、事柄ごとに。
    返す: 残した発行者情報。
    ほかに変えるもの: 発行者情報を、すべて一度に残す (P2.4)。
    断るとき:
        AnswersIncomplete: 欠けた事柄があるとき。何も残さない (P2.4)。
    """
    raise NotImplementedError("issuer.save")
```

`src/invoice/billing.py` は、請求書にさせる矢印を受ける。

```python
"""明細行から、取引先と締めの期間ごとの請求書の中身をどう決めるか。"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

from invoice.issuer import Issuer
from invoice.ledger import LedgerRow, TaxRate


@dataclass(frozen=True)
class Period:
    """締めの期間: 前の締め日の翌日から、次の締め日まで (P3.7)。"""

    start: datetime.date
    """期間の最初の日。"""
    end: datetime.date
    """締め日。"""


@dataclass(frozen=True)
class RateTotal:
    """税率ごとの合計: 一枚の請求書の中の一つの税率の、対象額と消費税額。"""

    rate: TaxRate
    """税率。"""
    tax_included: bool
    """対象額が税込なら True (P3.3)。"""
    base: int
    """税率ごとの対象額。円の整数。"""
    tax: int
    """消費税額。円未満を一度だけ切り捨てた円の整数 (P3.2)。"""


@dataclass(frozen=True)
class Invoice:
    """請求書: 一つの取引先の一つの締めの期間に請求する額と、その内訳。"""

    number: str
    """請求書番号 (P3.5)。"""
    customer: str
    """取引先の名称。"""
    period: Period
    """締めの期間。"""
    issue_date: datetime.date
    """発行日。締めの期間の締め日 (P3.6)。"""
    due_date: datetime.date
    """支払期限 (P3.9)。"""
    issuer: Issuer
    """発行者として載せる発行者情報。"""
    rows: tuple[LedgerRow, ...]
    """明細に載せる明細行。取引日が締めの期間に入るもの (P3.8)。"""
    totals: tuple[RateTotal, ...]
    """税率ごとの合計。一つ以上。"""
    amount: int
    """請求額。税込の円の整数。"""


def bill(rows: Sequence[LedgerRow], issuer: Issuer) -> tuple[Invoice, ...]:
    """請求書にさせる (S1)。

    受け取る: 直すところのない明細行と、発行者情報。
    返す: 取引先と締めの期間ごとに一枚ずつの請求書 (P3.4)。
        額と日付を決めるのは、このモジュールだけ (P3.1)。
    ほかに変えるもの: 番号の採番を通して、発行記録に番号を残させる。
    断るとき: なし。明細行の形は ledger.read が確かめ終えている。
    """
    raise NotImplementedError("billing.bill")
```

`src/invoice/numbering.py` は、番号を求める矢印を受ける。

```python
"""取引先と締めの期間の組に、どの請求書番号を付けるか。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from invoice.billing import Period


def number(customer: str, period: Period) -> str:
    """番号を求める (S1)。

    受け取る: 請求書の取引先と締めの期間。
    返す: その組の請求書番号。前に付けた組には、前と同じ番号 (P3.5, P1.4)。
        初めての組には、ほかの組に付けていない番号。
    ほかに変えるもの: 初めての組なら、その番号を発行記録に残してから返す。
        発行記録を読み書きするのは、このモジュールだけ (P3.5)。
    断るとき: なし。読めない場合と残せない場合はギャップに挙げる。
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

    受け取る: 請求書。
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

    kind: Literal["no_default_printer", "send_failed"]
    """既定のプリンターがない、または送れない。"""
    detail: str
    """印刷システムが返したわけ。なければ空。"""


class PrintRefused(Exception):
    """紙面を既定のプリンターに届けられないときに上がり、直すところを持つ。"""

    def __init__(self, fix: PrintFix) -> None:
        super().__init__(fix)
        self.fix = fix


def print_documents(documents: Sequence[PrintDocument]) -> int:
    """印刷させる (S1, S4)。

    受け取る: 印刷用の文書。
    返す: 送った用紙の枚数 (P2.6)。
    ほかに変えるもの: 文書を受け取った順に、send で既定のプリンターに送る。
    断るとき:
        PrintRefused: 既定のプリンターがないとき、一つも送らずに上がる。
            途中で送れなくなったとき、そこで上がる (S4)。
    """
    raise NotImplementedError("printing.print_documents")


def send(document: PrintDocument) -> None:
    """既定のプリンターに送る (S1, S4)。印刷システムへの矢印を運ぶ。

    印刷システムに触れるのは、この関数だけ (P2.3)。テストでは代役に替える。
    受け取る: 一つの印刷用の文書。
    返す: なし。
    ほかに変えるもの: 印刷システムに、既定のプリンターでの印刷を頼む。
    断るとき:
        PrintRefused: 既定のプリンターがないとき、または印刷システムが断ったとき。
    """
    raise NotImplementedError("printing.send")
```

## ギャップ

- S3 の「ないと返す」: この矢印はデータを持たず、尋ねる事柄がコマンドに届かない。事柄の一覧が、発行者情報の保管とコマンドの二か所に分かれる。
- 請求の計算: 消費税の決まりと、締めの期間と支払期限の決まりは、別のわけで変わる。ディレクトリ構成は両方を billing.py 一つに置き、一文で一つの決めごとを名指せない。
- デプロイの方針 [P2.2]: invoice の置き場の場所を決めるコンポーネントがない。発行者情報の保管と番号の採番が、同じ場所をそれぞれに持つことになる。
- S1 と S3: 発行者情報や発行記録を読めない、または残せないときの分かれ道がない。そのため load、save、number は断り方を持てず、利用者に直し方も示せない。
- S2 のインストーラー: コンポーネントにもディレクトリ構成にもなく、置き場のないものである。そのため「入れさせる」と「取り寄せる」の矢印を運ぶインターフェースを置けない。
