"""S4: つまずいても自分で直して進む道筋と、その原則と決めごとの結合ケース。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import command, ledger as ledger_module, place
from invoice.issuer import Issuer
from tests.given import README_ROWS, Printer, Terminal, billed, csv, files, paper, save_aoba

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
    for fix in refused.value.fixes:
        for shown in (str(fix.line), fix.column, fix.given, fix.expected):
            assert shown is not None and shown in out
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
    assert "プリンター" in out
    assert printer.sent == []
    # When: 利用者がプリンターを整えてから、同じコマンドを打ち直す。
    printer.refuse_at = None
    terminal()
    again = command.main([str(path)])
    # Then: 番号を飛ばさず、ガイドのとおりの番号で印刷する。
    assert again == 0
    assert billed(capsys.readouterr().out) == {"株式会社みなと商事 御中": ("2026-11-001", "51,980")}
    assert len(printer.sent) == 1


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
    # Then: プリンターの整え方を示して止まり、二枚目は送らない。
    assert code == 1
    assert "プリンター" in capsys.readouterr().out
    assert len(printer.sent) == 1


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
    assert any(str(each) in out for each in broken)
    assert printer.sent == []
