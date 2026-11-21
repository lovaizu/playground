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
    assert len({number for number, _ in shown.values()}) == 3
    assert "既定のプリンター「経理室プリンター」で 3 枚を印刷しました。" in out
    assert len(printer.sent) == 3
    for name, (amount, *totals) in MONTH_PAPERS.items():
        [text] = [paper(each) for each in printer.sent if f"{name}" in paper(each)]
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
    # Then: 何も尋ねずに、11 月と別の番号の請求書を一枚印刷する。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == []
    number, amount = billed(out)["株式会社みなと商事 御中"]
    assert (number != november[0], amount) == (True, "34,360")
    assert "既定のプリンター「経理室プリンター」で 1 枚を印刷しました。" in out
    [document] = printer.sent
    for line in (
        f"請求書番号: {number}",
        "発行日: 2026年12月31日",
        "お支払期限: 2027年1月31日",
        "10% 22,400 2,240",
        "8%(軽減税率) 9,000 720",
        "合計(税込): 34,360 円",
    ):
        assert line in paper(document)
