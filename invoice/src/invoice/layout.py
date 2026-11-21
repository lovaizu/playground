"""請求書の値を、テンプレートのどの名前と形に移して紙面に描くか。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jinja2

from invoice import sheet
from invoice.billing import Invoice

_HERE = Path(__file__).resolve().parent

_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.ChoiceLoader(
        [
            # 配布物の中: 配布物は invoice の一式の templates/ を、本体の templates/ に入れる。
            jinja2.FileSystemLoader(_HERE / "templates"),
            # invoice の一式の中: 開発者が uv run で動かすとき。
            jinja2.FileSystemLoader(_HERE.parents[1] / "templates"),
        ]
    ),
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=jinja2.StrictUndefined,
    keep_trailing_newline=True,
)
"""invoice/templates/ のテンプレートを、テンプレートが求めるとおりに描く環境。"""


@dataclass(frozen=True)
class PrintDocument:
    """印刷用の文書: 一枚の請求書を用紙の上に配置し、プリンターへそのまま渡せるもの。"""

    pdf: bytes
    """紙面の PDF。書体は invoice とともに配るものを埋め込む。"""
    sheets: int
    """用紙の枚数。PDF のページの数で、一以上。"""


def typeset(invoices: Sequence[Invoice]) -> tuple[PrintDocument, ...]:
    """紙面にさせる (S1)。

    受け取る: 請求書。紙面に載せる値は、すべて請求書の中にある。
        宛先: customer.name と customer.honorific。
        発行者: issuer.name、issuer.registration_number、
            お振込先の issuer.bank の name、branch、account_type、
            account_number、account_holder。
        請求書番号と日付: number、issue_date、due_date。
        明細: 各 lines の row の date、description、quantity、unit、unit_price、
            tax_rate と、その行の amount。単価と金額の税込か税抜は tax_included。
            tax_rate が 8 の行には、軽減税率の旨を添える。
        税率ごとの合計: 各 totals の rate、base、tax。
        ご請求金額と合計(税込): amount。
    返す: 請求書ごとに一つの印刷用の文書を、受け取った順に。
        紙面は invoice/templates/invoice.md.j2 が描く Markdown を、sheet.pdf が用紙に配置したもの。
        額は請求書のものをそのまま載せ、計算しない (P3.1)。
    ほかに変えるもの: なし。
    断るとき: なし。
    """
    template = _ENVIRONMENT.get_template("invoice.md.j2")
    documents = []
    for invoice in invoices:
        pdf, pages = sheet.pdf(template.render(invoice=_values(invoice)))
        documents.append(PrintDocument(pdf=pdf, sheets=pages))
    return tuple(documents)


def _values(invoice: Invoice) -> dict[str, Any]:
    """請求書を、テンプレートが読む値の名前と形に移したもの。macros.j2 の冒頭のとおり。"""
    return {
        "customer": invoice.customer,
        "issuer": invoice.issuer,
        "number": invoice.number,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "tax_included": invoice.tax_included,
        "lines": [
            {
                "date": line.row.date,
                "item": line.row.description,
                "quantity": line.row.quantity,
                "unit": line.row.unit,
                "unit_price": line.row.unit_price,
                "tax_rate": line.row.tax_rate,
                "reduced": line.row.tax_rate == 8,
                "amount": line.amount,
            }
            for line in invoice.lines
        ],
        "tax_summaries": [
            {"tax_rate": total.rate, "reduced": total.rate == 8, "base": total.base, "tax": total.tax}
            for total in invoice.totals
        ],
        "total": invoice.amount,
    }
