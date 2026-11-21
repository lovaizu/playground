"""テンプレートが描いた Markdown を、用紙の上にどう配置して PDF にするか。"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

_FONT = Path(__file__).resolve().parent / "fonts" / "ipaexg.ttf"
"""紙面の書体。invoice とともに配る IPAex ゴシック。ノートPCの書体には頼らない。"""

_MARGIN = 15.0
"""用紙の上下左右の余白 (mm)。"""

_PADDING = 4.0
"""表の各列で、いちばん長い値の幅に足す余白 (mm)。"""

_AMOUNT = re.compile(r"[0-9][0-9,]*( \S+)?")
"""右に寄せる額と数量の値。例: `2,800`、`10 箱`。"""


def pdf(markdown: str) -> tuple[bytes, int]:
    """Markdown の請求書を、A4 の用紙に配置した PDF。

    受け取る: invoice.md.j2 が描いた Markdown。読むのは、`#` の表題、`##` の見出し、
        `|` で区切った表 (二行目は `| --- |` の区切り)、行末の `\\` で改行する段落の行、
        段落を分ける空の行だけ。
    返す: 書体を埋め込んだ PDF と、そのページの数。
        表は罫線で囲み、額と数量の列は右に寄せ、ページをまたぐ表は各ページに見出しの行を繰り返す。
        紙面に `#`、`|`、行末の `\\` は出ない。
    ほかに変えるもの: なし。
    断るとき: なし。
    """
    document = FPDF(format="A4", unit="mm")
    document.set_margins(_MARGIN, _MARGIN, _MARGIN)
    document.set_auto_page_break(True, margin=_MARGIN)
    document.add_font("IPAexGothic", fname=str(_FONT))
    document.set_title("請求書")
    document.set_creator("invoice")
    document.add_page()
    lines = markdown.splitlines()
    at = 0
    while at < len(lines):
        if lines[at].startswith("|"):
            table = []
            while at < len(lines) and lines[at].startswith("|"):
                table.append(_cells(lines[at]))
                at += 1
            _table(document, [table[0], *table[2:]])
            continue
        _line(document, lines[at])
        at += 1
    return bytes(document.output()), document.pages_count


def _cells(line: str) -> list[str]:
    """`| a | b |` の表の行の、各列の値。"""
    return [cell.strip() for cell in line.strip()[1:-1].split("|")]


def _line(document: FPDF, line: str) -> None:
    """表のほかの一行を、表題、見出し、段落の行、空きのどれかとして置く。"""
    if line.startswith("# "):
        document.set_font("IPAexGothic", size=20)
        document.cell(text=line[2:], new_x="LMARGIN", new_y="NEXT", align="C", w=0, h=12)
    elif line.startswith("## "):
        document.set_font("IPAexGothic", size=12)
        document.cell(text=line[3:], new_x="LMARGIN", new_y="NEXT", w=0, h=8, border="B")
        document.ln(1)
    elif line == "":
        document.ln(3)
    else:
        document.set_font("IPAexGothic", size=10)
        document.multi_cell(w=0, h=6, text=line.removesuffix("\\"), new_x="LMARGIN", new_y="NEXT")


def _table(document: FPDF, rows: list[list[str]]) -> None:
    """見出しの行と値の行を、罫線の表として置く。"""
    document.set_font("IPAexGothic", size=9)
    columns = list(zip(*rows, strict=True))
    widths = [max(document.get_string_width(cell) for cell in column) + _PADDING for column in columns]
    widest = widths.index(max(widths))
    widths[widest] += document.epw - sum(widths)
    align = tuple("RIGHT" if all(_AMOUNT.fullmatch(cell) for cell in column[1:]) else "LEFT" for column in columns)
    with document.table(
        col_widths=tuple(widths),
        width=document.epw,
        text_align=align,
        line_height=6,
        headings_style=FontFace(emphasis="", fill_color=(235, 235, 235)),
    ) as table:
        for values in rows:
            row = table.row()
            for value in values:
                row.cell(value)
