"""S1: 明細から請求書を印刷する道筋と、その原則と決めごとの結合ケース。"""

from __future__ import annotations

import datetime
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import billing, command, issuer, layout, ledger as ledger_module, numbering, printing
from invoice.issuer import Issuer
from invoice.periods import Period
from tests.given import (
    AOBA,
    AOBA_ANSWERS,
    INCLUDED_HEADER,
    README_LEDGER_ROWS,
    README_PAPER,
    README_ROWS,
    Printer,
    Terminal,
    asked,
    billed,
    csv,
    paper,
    save_aoba,
)

supports = pytest.mark.supports


@supports(
    "S1",
    "P2.3",
    "P2.6",
    "P3.1",
    "明細",
    "明細行",
    "発行者情報",
    "請求書",
    "税率ごとの合計",
    "印刷用の文書",
    "コマンド",
    "明細の読み取り",
    "発行者情報の保管",
    "請求の計算",
    "番号の採番",
    "請求書の組版",
    "印刷",
)
def test_明細から請求書が印刷され番号と金額と枚数が示される(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報を残したあとの、ガイドの 11 月分の明細。
    path = ledger(csv(*README_ROWS))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 一枚の請求書を既定のプリンターに送り、番号と金額と枚数を示す。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == []
    assert billed(out) == {"株式会社みなと商事 御中": ("2026-11-001", "51,980")}
    assert out.endswith("既定のプリンター「経理室プリンター」で 1 枚を印刷しました。\n")
    [document] = printer.sent
    assert document.sheets == 1
    for line in README_PAPER:
        assert line in paper(document)


@supports("S1", "P3.4", "P3.6", "P3.7", "P3.8", "P3.9")
def test_取引先と締めの期間ごとに一枚ずつ印刷される(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 20日締め翌月10日払いの発行者と、締め日の前後にまたがる二つの取引先の明細。
    save_aoba(payment_terms="20日締め翌月10日払い")
    path = ledger(
        csv(
            "株式会社みなと商事,2026-11-20,コピー用紙 A4 500枚,10,箱,2800,10%",
            "株式会社ひかり設計,2026-11-05,トナーカートリッジ 黒,2,本,12800,10%",
            "株式会社みなと商事,2026-11-21,ボールペン 黒 10本入,5,箱,1200,10%",
        )
    )
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 取引先と締めの期間の組ごとに一枚ずつ、その期間の行だけを載せて印刷する。
    out = capsys.readouterr().out
    assert code == 0
    assert "3 枚を印刷しました。" in out
    texts = [paper(each) for each in printer.sent]
    expected = (
        (
            "株式会社みなと商事 御中",
            "2026年11月20日",
            "2026年12月10日",
            "30,800",
            "コピー用紙 A4 500枚",
            "ボールペン 黒 10本入",
        ),
        (
            "株式会社みなと商事 御中",
            "2026年12月20日",
            "2027年1月10日",
            "6,600",
            "ボールペン 黒 10本入",
            "コピー用紙 A4 500枚",
        ),
        (
            "株式会社ひかり設計 御中",
            "2026年11月20日",
            "2026年12月10日",
            "28,160",
            "トナーカートリッジ 黒",
            "コピー用紙 A4 500枚",
        ),
    )
    for name, issued, due, amount, kept, left in expected:
        [text] = [each for each in texts if name in each and f"発行日: {issued}" in each]
        assert f"お支払期限: {due}" in text
        assert f"ご請求金額(税込): {amount} 円" in text
        assert kept in text
        assert left not in text


@supports("S1", "P3.2", "税率ごとの合計")
def test_消費税額は税率ごとに一度だけ切り捨てて載る(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 行ごとに切り捨てると 264 円、合計で切り捨てると 266 円になる、軽減税率の三行。
    path = ledger(
        csv(
            "株式会社みなと商事,2026-11-02,緑茶ティーバッグ 50袋入,1,箱,1111,8%",
            "株式会社みなと商事,2026-11-09,緑茶ティーバッグ 50袋入,1,箱,1111,8%",
            "株式会社みなと商事,2026-11-16,緑茶ティーバッグ 50袋入,1,箱,1111,8%",
        )
    )
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 消費税額は税率ごとの対象額から一度だけ切り捨てた 266 円になる。
    assert code == 0
    assert billed(capsys.readouterr().out) == {"株式会社みなと商事 御中": ("2026-11-001", "3,599")}
    text = paper(printer.sent[0])
    assert "8%(軽減税率) 3,333 266" in text
    assert "合計(税込): 3,599 円" in text


@supports("S1", "P3.3")
def test_税込の単価の明細では税込の合計から消費税額が出る(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 単価が税込の明細。
    path = ledger(
        csv(
            "株式会社みなと商事,2026-11-05,コピー用紙 A4 500枚,3,箱,1100,10%",
            "株式会社みなと商事,2026-11-12,ドリップコーヒー 100袋入,1,箱,1080,8%",
            "株式会社みなと商事,2026-11-20,ボールペン 黒 10本入,1,箱,1000,10%",
            header=INCLUDED_HEADER,
        )
    )
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 税率ごとの税込の対象額から消費税額を出し、税込の対象額の和を請求する。
    assert code == 0
    assert billed(capsys.readouterr().out) == {"株式会社みなと商事 御中": ("2026-11-001", "5,380")}
    text = paper(printer.sent[0])
    for line in (
        "取引日 品目 数量 単価(税込) 税率 金額(税込)",
        "税率 対象額(税込) 消費税額",
        "10% 4,300 390",
        "8%(軽減税率) 1,080 80",
        "合計(税込): 5,380 円",
    ):
        assert line in text


@supports("S1", "P3.1", "請求の計算", "請求書の組版")
def test_画面と紙面の金額は請求の計算が決めた額と同じ(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 二つの取引先の明細。
    path = ledger(csv(*README_ROWS, "株式会社ひかり設計,2026-11-16,緑茶ティーバッグ 50袋入,6,箱,980,8%"))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 画面と紙面に、請求の計算が決めた番号と額がそのまま載る。
    shown = billed(capsys.readouterr().out)
    decided = {
        f"{each.customer.name} {each.customer.honorific}": (each.number, f"{each.amount:,}")
        for each in billing.bill(ledger_module.read(path), aoba)
    }
    assert code == 0
    assert shown == decided
    for name, (number, amount) in decided.items():
        [text] = [paper(each) for each in printer.sent if name in paper(each)]
        assert f"請求書番号: {number}" in text
        assert f"ご請求金額(税込): {amount} 円" in text
        assert f"合計(税込): {amount} 円" in text


@supports("S1", "P3.5", "発行記録", "番号の採番")
def test_同じ明細を二度印刷しても同じ請求書番号になる(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 一度印刷した、ガイドの 11 月分の明細。
    path = ledger(csv(*README_ROWS))
    terminal()
    assert command.main([str(path)]) == 0
    first = capsys.readouterr().out
    # When: 利用者が同じ明細で、もう一度印刷する。
    terminal()
    code = command.main([str(path)])
    # Then: 前と同じ番号の、同じ中身の請求書が出る。
    second = capsys.readouterr().out
    assert code == 0
    assert billed(second) == billed(first) == {"株式会社みなと商事 御中": ("2026-11-001", "51,980")}
    assert paper(printer.sent[1]) == paper(printer.sent[0])
    november = Period(datetime.date(2026, 11, 1), datetime.date(2026, 11, 30))
    assert numbering.number("株式会社みなと商事", november) == "2026-11-001"


@supports("S1", "P2.3", "印刷")
def test_印刷システムに触れるのは印刷だけ(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: printing.send を代役に替え、印刷システムのコマンドを呼ぶと失敗するノートPC。
    printing_commands = {"lp", "lpr", "lpstat", "lpoptions", "lpadmin", "cancel"}

    class Guarded(subprocess.Popen):  # type: ignore[type-arg]
        def __init__(self, args, *rest, **named):  # type: ignore[no-untyped-def]
            first = args if isinstance(args, str | bytes | os.PathLike) else next(iter(args))
            assert os.path.basename(os.fsdecode(first)).split()[0] not in printing_commands
            super().__init__(args, *rest, **named)

    monkeypatch.setattr(subprocess, "Popen", Guarded)
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then: ほかの部品は印刷システムに触れず、紙面は代役にだけ届く。
    assert code == 0
    assert len(printer.sent) == 1


@supports("S1", "P2.2", "発行者情報", "発行記録")
def test_どのフォルダーで打っても同じ発行者情報と番号を使う(
    home: Path,
    tmp_path: Path,
    terminal: Callable[..., Terminal],
    printer: Printer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 11 月分を、あるフォルダーで初回の答えとともに印刷したあと。
    november, december = tmp_path / "11月", tmp_path / "12月"
    for folder in (november, december):
        folder.mkdir()
    (november / "明細.csv").write_text(csv(*README_ROWS), encoding="utf-8")
    (december / "明細.csv").write_text(
        csv("株式会社みなと商事,2026-12-03,コピー用紙 A4 500枚,8,箱,2800,10%"), encoding="utf-8"
    )
    monkeypatch.chdir(november)
    terminal(*AOBA_ANSWERS)
    assert command.main(["明細.csv"]) == 0
    first = billed(capsys.readouterr().out)
    # When: 利用者が別のフォルダーで、12 月分の明細を渡す。
    monkeypatch.chdir(december)
    terminal()
    code = command.main(["明細.csv"])
    # Then: 何も尋ねず、11 月と重ならない番号で印刷する。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == []
    assert billed(out)["株式会社みなと商事 御中"][0] != first["株式会社みなと商事 御中"][0]
    assert issuer.load() == AOBA


@supports("P1.2", "コマンド")
def test_利用者と言葉を交わすのはコマンドだけ(
    aoba: Issuer,
    ledger: Callable[..., Path],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 誤りのある明細と、誤りのない明細。
    wrong = ledger(csv("株式会社みなと商事,2026-11-31,コピー用紙 A4 500枚,10,箱,2800,10%"), name="誤り.csv")
    right = ledger(csv(*README_ROWS))
    # When: コマンドのほかの部品を、断るときも含めて一つずつ呼ぶ。
    with pytest.raises(ledger_module.LedgerRefused):
        ledger_module.read(wrong)
    with pytest.raises(issuer.AnswerRefused):
        issuer.check("payment_terms", "末締め")
    invoices = billing.bill(ledger_module.read(right), aoba)
    printing.print_documents(layout.typeset(invoices))
    # Then: どの部品も、端末に何も示さない。
    assert capsys.readouterr() == ("", "")
    assert [each.lines for each in invoices] == [
        tuple(
            billing.InvoiceLine(row, amount)
            for row, amount in zip(README_LEDGER_ROWS, (28000, 13500, 6000), strict=True)
        )
    ]
