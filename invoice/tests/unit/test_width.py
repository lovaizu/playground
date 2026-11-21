"""全角と半角の読み替え (width.narrowed) の単体ケース。"""

from __future__ import annotations

import pytest

from invoice.width import narrowed

supports = pytest.mark.supports


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_全角の数字と英字と記号は半角に読み替える() -> None:
    # Given: 全角で打った登録番号、税率、括弧、ハイフン、スラッシュ。
    # When
    text = narrowed("Ｔ１２３ １０％（株）２０２６－１１／０５")
    # Then
    assert text == "T123 10%(株)2026-11/05"


@supports("test_形に合わない答えは例を示して同じ事柄を尋ね直す")
def test_半角カナは濁点と半濁点を前の字と一つにして全角に読み替える() -> None:
    # Given: 半角カナで打った口座名義と、半濁点のある字。
    # When
    text = narrowed("ｶ)ｱｵﾊﾞｼﾞﾑﾖｳﾋﾝ ﾊﾟｰﾄ")
    # Then
    assert text == "カ)アオバジムヨウヒン パート"


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_全角の英数字と記号と半角カナのほかの字はそのまま返す() -> None:
    # Given: 漢字、ひらがな、全角カナ、丸数字、全角の空白、半角の英数字。
    # When
    text = narrowed("株式会社みなと商事　コピー用紙①A4 500枚")
    # Then
    assert text == "株式会社みなと商事　コピー用紙①A4 500枚"
