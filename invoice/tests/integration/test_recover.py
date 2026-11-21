"""S4: つまずいても自分で直して進む道筋と、その原則と決めごとの結合ケース。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import command, ledger as ledger_module, place
from invoice.issuer import Issuer
from tests.given import (
    DATE_RULE,
    LEDGER_STOPPED,
    NO_PRINTER,
    QUANTITY_RULE,
    RATE_RULE,
    README_LINES,
    README_ROWS,
    README_SHEETS,
    README_TOTALS,
    Printer,
    Terminal,
    bad_value,
    bill_line,
    billed,
    csv,
    files,
    paper,
    printed,
    save_aoba,
    send_failed,
    sheets,
    store_stopped,
)

supports = pytest.mark.supports


@supports("S4", "P1.2", "P1.3", "直すところ", "明細の読み取り")
def test_明細の直すところをすべて示し何も印刷しない(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 二つの行の三つの列に誤りのある明細。
    path = ledger(
        csv(
            "株式会社みなと商事,2026-11-31,コピー用紙 A4 500枚,10,箱,2800,10%",
            README_ROWS[1],
            "株式会社みなと商事,2026-11-20,ボールペン 黒 10本入,五,箱,1200,5%",
        )
    )
    with pytest.raises(ledger_module.LedgerRefused) as refused:
        ledger_module.read(path)
    kept = files(place.folder())
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: すべての直すところを、行と列と値と例とともに一度に示し、何も印刷しない。
    out = capsys.readouterr().out
    assert code == 1
    assert {(fix.line, fix.column, fix.given) for fix in refused.value.fixes} == {
        (2, "取引日", "2026-11-31"),
        (4, "数量", "五"),
        (4, "税率", "5%"),
    }
    assert out == (
        LEDGER_STOPPED
        + bad_value(path, 2, "取引日", "2026-11-31", DATE_RULE, "2026-11-20")
        + bad_value(path, 4, "数量", "五", QUANTITY_RULE, "10")
        + bad_value(path, 4, "税率", "5%", RATE_RULE, "10%")
    )
    assert printer.sent == []
    assert files(place.folder()) == kept


@supports("S4", "P1.4")
def test_示されたとおり直して打ち直すとはじめから正しいときと同じ請求書が出る(
    home: Path,
    tmp_path: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: はじめから正しい明細で印刷した、別の利用者の請求書。
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("HOME", str(other))
    save_aoba()
    path = ledger(csv(*README_ROWS))
    terminal()
    assert command.main([str(path)]) == 0
    right = (billed(capsys.readouterr().out), paper(printer.sent.pop()))
    # Given: 取引日に誤りのある明細で止まったあとの利用者。
    monkeypatch.setenv("HOME", str(home))
    save_aoba()
    path.write_text(csv(README_ROWS[0].replace("2026-11-05", "2026-11-31"), *README_ROWS[1:]), encoding="utf-8")
    terminal()
    assert command.main([str(path)]) == 1
    capsys.readouterr()
    # When: 利用者が示されたとおりに直し、同じコマンドを打ち直す。
    path.write_text(csv(*README_ROWS), encoding="utf-8")
    terminal()
    code = command.main([str(path)])
    # Then: はじめから正しく打ったときと同じ請求書が出る。
    assert code == 0
    assert (billed(capsys.readouterr().out), paper(printer.sent.pop())) == right


@supports("S4", "P1.2", "P1.4", "印刷")
def test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 既定のプリンターのないノートPC。
    printer.refuse_at, printer.problem = 0, "no_default_printer"
    path = ledger(csv(*README_ROWS))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: プリンターの整え方を示し、何も印刷せずに止まる。
    out = capsys.readouterr().out
    assert code == 1
    assert out == NO_PRINTER
    assert printer.sent == []
    # When: 利用者がプリンターを整えてから、同じコマンドを打ち直す。
    printer.refuse_at = None
    terminal()
    again = command.main([str(path)])
    # Then: 番号を飛ばさず、ガイドのとおりの番号で印刷する。
    assert again == 0
    assert capsys.readouterr().out == bill_line("株式会社みなと商事 御中", "2026-11-001", "51,980") + printed(1) + "\n"
    [document] = printer.sent
    assert paper(document) in README_SHEETS


@supports("S4", "P1.2")
def test_送る途中で送れなくなると整え方を示して止まる(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 一枚目を送ったあと、印刷システムが断るノートPCと、二つの取引先の明細。
    printer.refuse_at = 1
    path = ledger(csv(*README_ROWS, "株式会社ひかり設計,2026-11-16,緑茶ティーバッグ 50袋入,6,箱,980,8%"))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: プリンターの整え方を示して止まり、二枚目は送らない。請求書の順は契約で決まっていない。
    assert code == 1
    assert capsys.readouterr().out == send_failed("代役が断った")
    [document] = printer.sent
    minato = [
        sheets(
            "株式会社みなと商事 御中",
            number,
            "2026年11月30日",
            "51,980",
            "2026年12月31日",
            README_LINES,
            README_TOTALS,
        )
        for number in ("2026-11-001", "2026-11-002")
    ]
    hikari = [
        sheets(
            "株式会社ひかり設計 御中",
            number,
            "2026年11月30日",
            "6,350",
            "2026年12月31日",
            ("2026年11月16日 緑茶ティーバッグ 50袋入 6 箱 980 8%(軽減税率) 5,880",),
            ("8%(軽減税率) 5,880 470",),
        )
        for number in ("2026-11-001", "2026-11-002")
    ]
    assert any(paper(document) in each for each in (*minato, *hikari)), "一枚目の請求書の紙面"


@supports("S1", "S3", "発行者情報の保管")
def test_置き場のファイルが壊れていると直し方を示し何も印刷しない(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 残した発行者情報のファイルが壊れたノートPC。
    broken = list(files(place.folder()))
    for each in broken:
        each.write_bytes(b"\x00broken")
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then: どのファイルが問題かを示し、何も尋ねず、何も印刷せずに止まる。
    out = capsys.readouterr().out
    assert code == 1
    [path] = broken
    assert out == store_stopped(path) + (
        "このファイルの中身が壊れていて、読めません。"
        "バックアップがあれば戻してから、同じコマンドを打ち直してください。"
        "戻せないときは、この画面の文を貼って https://github.com/lovaizu/playground/issues で尋ねてください。\n"
    )
    assert printer.sent == []
