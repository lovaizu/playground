"""経理チームが、ガイドだけを頼りに、明細からコマンド一つで請求書を印刷する E2E ケース。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import command, issuer
from tests.given import (
    AOBA,
    AOBA_ANSWERS,
    ASKED,
    DATE_RULE,
    LEDGER_STOPPED,
    QUANTITY_RULE,
    README_ROWS,
    README_SHEETS,
    Printer,
    Terminal,
    bad_value,
    bill_line,
    billed,
    csv,
    paper,
    printed,
    sheets,
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
    "株式会社みなと商事 御中": (
        "61,220",
        (
            "2026年11月5日 コピー用紙 A4 500枚 10 箱 2,800 10% 28,000",
            "2026年11月12日 ドリップコーヒー 100袋入 3 箱 4,500 8%(軽減税率) 13,500",
            "2026年11月20日 ボールペン 黒 10本入 5 箱 1,200 10% 6,000",
            "2026年11月25日 クリアファイル A4 100枚入 4 箱 1,350 10% 5,400",
            "2026年11月26日 ホッチキス針 No.10 20箱入 2 箱 1,500 10% 3,000",
        ),
        ("10% 42,400 4,240", "8%(軽減税率) 13,500 1,080"),
    ),
    "株式会社ひかり設計 御中": (
        "61,218",
        (
            "2026年11月2日 トナーカートリッジ 黒 2 本 12,800 10% 25,600",
            "2026年11月9日 コピー用紙 A3 500枚 3 箱 4,200 10% 12,600",
            "2026年11月13日 プリンター用紙 B4 500枚 2 箱 3,600 10% 7,200",
            "2026年11月16日 緑茶ティーバッグ 50袋入 6 箱 980 8%(軽減税率) 5,880",
            "2026年11月27日 付箋 75mm 10冊入 7 箱 640 10% 4,480",
        ),
        ("10% 49,880 4,988", "8%(軽減税率) 5,880 470"),
    ),
    "株式会社やまびこ食品 御中": (
        "31,345",
        (
            "2026年11月4日 ミネラルウォーター 2L 6本入 7 箱 1,180 8%(軽減税率) 8,260",
            "2026年11月18日 ドリップコーヒー 100袋入 2 箱 4,500 8%(軽減税率) 9,000",
            "2026年11月24日 紙コップ 205ml 100個入 10 袋 450 10% 4,500",
            "2026年11月30日 段ボール箱 120サイズ 10枚入 3 束 2,350 10% 7,050",
        ),
        ("10% 11,550 1,155", "8%(軽減税率) 17,260 1,380"),
    ),
}
"""11 月分の明細から、取引先ごとに出る請求書のご請求金額と、明細の行と、税率ごとの合計の行。"""


def printed_month(out: str, printer: Printer, before: str) -> None:
    """11 月分の明細から、三つの取引先の請求書が、それぞれ正しい額で一枚ずつ出たこと。

    端末には before のあとに請求書ごとの行と枚数の行だけが出る。請求書の順は契約で決まっていない。
    """
    shown = billed(out)
    assert {name: amount for name, (_, amount) in shown.items()} == {
        name: amount for name, (amount, *_) in MONTH_PAPERS.items()
    }
    assert {number for number, _ in shown.values()} == {"2026-11-001", "2026-11-002", "2026-11-003"}
    assert out.startswith(before), "請求書の行より前の文"
    assert sorted(out[len(before) :].splitlines(keepends=True)) == sorted(
        [*(bill_line(name, number, amount) for name, (number, amount) in shown.items()), printed(3) + "\n"]
    )
    assert out.endswith(printed(3) + "\n")
    texts = [paper(each) for each in printer.sent]
    assert len(texts) == 3
    for name, (amount, lines, totals) in MONTH_PAPERS.items():
        expected = sheets(name, shown[name][0], "2026年11月30日", amount, "2026年12月31日", lines, totals)
        assert len([text for text in texts if text in expected]) == 1, f"{name} の紙面が一枚"


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
    printed_month(out, printer, ASKED)
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
    # Then: 誤りの行と列と値と直し方をすべて示し、何も尋ねず、何も印刷しない。
    out = capsys.readouterr().out
    assert first == 1
    assert out == (
        LEDGER_STOPPED
        + bad_value(path, 5, "取引日", "2026-11-31", DATE_RULE, "2026-11-20")
        + bad_value(path, 14, "数量", "七", QUANTITY_RULE, "10")
    )
    assert printer.sent == []
    # When: 利用者が示されたとおりに直し、同じコマンドを打ち直す。
    path.write_text(csv(*MONTH_ROWS), encoding="utf-8")
    terminal(*AOBA_ANSWERS)
    second = command.main([str(path)])
    # Then: はじめから正しく打ったときと同じく、取引先ごとの請求書が出る。
    out = capsys.readouterr().out
    assert second == 0
    printed_month(out, printer, ASKED)


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
    november = bill_line("株式会社みなと商事 御中", "2026-11-001", "51,980")
    assert capsys.readouterr().out == ASKED + november + printed(1) + "\n"
    assert paper(printer.sent[0]) in README_SHEETS
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
    assert out == bill_line("株式会社みなと商事 御中", "2026-12-001", "34,360") + printed(1) + "\n"
    [document] = printer.sent
    assert paper(document) in sheets(
        "株式会社みなと商事 御中",
        "2026-12-001",
        "2026年12月31日",
        "34,360",
        "2027年1月31日",
        (
            "2026年12月3日 コピー用紙 A4 500枚 8 箱 2,800 10% 22,400",
            "2026年12月10日 ドリップコーヒー 100袋入 2 箱 4,500 8%(軽減税率) 9,000",
        ),
        ("10% 22,400 2,240", "8%(軽減税率) 9,000 720"),
    )
