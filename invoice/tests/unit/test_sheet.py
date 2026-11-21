"""Markdown の紙面への配置 (sheet.pdf) の単体ケース。"""

from __future__ import annotations

import io

import pytest
from pypdf import PdfReader

from invoice import sheet

supports = pytest.mark.supports


def page_texts(pdf: bytes) -> list[str]:
    """PDF の各ページに載る文字を、空白の並びを一つの空白につめて。"""
    return [" ".join(page.extract_text().split()) for page in PdfReader(io.BytesIO(pdf)).pages]


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_表題と見出しと段落の行と罫線の表を印を除いて一ページに置く() -> None:
    # Given: 表題、見出し、行末の \ で改行する段落、表を持つ Markdown。
    markdown = (
        "# 請求書\n\n## 発行者\n\n株式会社あおば事務用品\\\n登録番号: T1234567890123\n\n"
        "| 税率 | 消費税額 |\n| --- | --- |\n| 10% | 3,400 |\n"
    )
    # When
    pdf, pages = sheet.pdf(markdown)
    # Then
    assert pages == 1
    assert page_texts(pdf) == ["請求書 発行者 株式会社あおば事務用品 登録番号: T1234567890123 税率 消費税額 10% 3,400"]


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_ページをまたぐ表は次のページにも見出しの行を置く() -> None:
    # Given: 一ページに収まらない、百行の表。
    rows = "".join(f"| 品目 {i:03} | {i:,} |\n" for i in range(100))
    markdown = f"## 明細\n\n| 品目 | 金額(税抜) |\n| --- | --- |\n{rows}"
    # When
    pdf, pages = sheet.pdf(markdown)
    # Then
    texts = page_texts(pdf)
    assert pages == len(texts) >= 2
    assert texts[1].startswith("品目 金額(税抜)"), "二ページ目の初めに見出しの行がある"
    assert "品目 099 99" in texts[-1]
