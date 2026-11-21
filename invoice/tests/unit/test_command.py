"""コマンド (command.main) の単体ケース。"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import command, issuer, ledger as ledger_module, place
from invoice.issuer import Issuer
from tests.given import (
    AOBA,
    AOBA_ANSWERS,
    AOBA_LABELS,
    README_ROWS,
    Printer,
    Terminal,
    asked,
    billed,
    csv,
    files,
)

supports = pytest.mark.supports


@supports("test_版を尋ねると版が示される")
def test_版を尋ねると版だけを示して0を返す(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Given: 何も残していないノートPC。
    # When
    code = command.main(["--version"])
    # Then
    assert code == 0
    assert capsys.readouterr() == ("invoice 0.1.0\n", "")
    assert files(place.folder()) == {}


@supports("test_版を尋ねると版が示される")
@pytest.mark.parametrize(
    "argv", [[], ["2026年11月分明細.csv", "2026年12月分明細.csv"], ["--version", "x.csv"], ["--help"]]
)
def test_引数が明細一つでも版でもなければ使い方を示して2を返す(
    home: Path, printer: Printer, argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: 何も残していないノートPC。
    # When
    code = command.main(argv)
    # Then
    out, err = capsys.readouterr()
    assert code == 2
    assert out + err != ""
    assert asked(out + err) == []
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_ない明細のファイルではそのパスを示して1を返す(
    aoba: Issuer,
    tmp_path: Path,
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: ないファイルのパス。
    missing = tmp_path / "2026年11月分明細.csv"
    terminal()
    # When
    code = command.main([str(missing)])
    # Then
    assert code == 1
    assert str(missing) in capsys.readouterr().out
    assert printer.sent == []


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_読めない明細のファイルではそのパスとUTF8のCSVでの保存し直し方を示し何も尋ねずに1を返す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、Shift_JIS で保存したガイドの明細。
    path = ledger(csv(*README_ROWS), encoding="shift_jis")
    with pytest.raises(ledger_module.LedgerRefused) as refused:
        ledger_module.read(path)
    terminal()
    # When
    code = command.main([str(path)])
    # Then: ファイルを読めないことと、UTF-8 の CSV で保存し直す手順を示し、何も尋ねず、何も残さず、何も印刷しない。
    out = capsys.readouterr().out
    assert [fix.problem for fix in refused.value.fixes] == ["unreadable"]
    assert code == 1
    assert str(path) in out
    assert "UTF-8" in out
    assert "CSV" in out
    assert asked(out) == []
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_見出しの行しかない明細では行がないことと一行の例を示し何も尋ねずに1を返す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、見出しの行だけを保存した明細。
    path = ledger(csv())
    with pytest.raises(ledger_module.LedgerRefused) as refused:
        ledger_module.read(path)
    [fix] = refused.value.fixes
    terminal()
    # When
    code = command.main([str(path)])
    # Then: 明細に行がないことを、そのまま書き足せる一行の例とともに示し、何も尋ねず、何も残さず、何も印刷しない。
    out = capsys.readouterr().out
    assert fix.problem == "no_rows"
    assert code == 1
    assert str(path) in out
    assert fix.expected != "" and fix.expected in out
    assert asked(out) == []
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_初回は事柄を順に尋ねすべての答えがそろってから残す")
def test_発行者情報がない状態で明細を渡すとloadの事柄を順に尋ねて残す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報のない状態。
    questions = issuer.load()
    assert isinstance(questions, tuple)
    terminal(*AOBA_ANSWERS)
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == [question.label for question in questions] == list(AOBA_LABELS)
    assert issuer.load() == AOBA
    assert billed(out) == {"株式会社みなと商事 御中": ("2026-11-001", "51,980")}


@supports("test_二回目からは何も尋ねずに印刷まで進む")
def test_発行者情報がある状態で明細を渡すと何も尋ねずに印刷して0を返す(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報のある状態。
    terminal()
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == []
    assert "1 枚を印刷しました。" in out
    assert issuer.load() == AOBA
    assert len(printer.sent) == 1


@supports("test_答えずに止めると何も残さず次は最初から尋ねる")
@pytest.mark.parametrize("answered", [0, 7])
def test_尋ねる途中で止めると何も残さず130を返す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    answered: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 最初の事柄か、最後の事柄で止める利用者。
    terminal(*AOBA_ANSWERS[:answered])
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    assert code == 130
    assert asked(capsys.readouterr().out) == list(AOBA_LABELS[: answered + 1])
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_形に合わない答えは例を示して同じ事柄を尋ね直す")
def test_断られた答えのあとは同じ事柄だけを尋ね直す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 口座番号に 6 桁を答えてから、7 桁を答える利用者。
    terminal(*AOBA_ANSWERS[:6], "123456", *AOBA_ANSWERS[6:])
    with pytest.raises(issuer.AnswerRefused) as refused:
        issuer.check("account_number", "123456")
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == [*AOBA_LABELS[:7], *AOBA_LABELS[6:]]
    assert refused.value.fix.expected in out
    assert issuer.load() == AOBA


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行記録が壊れているとそのファイルを示して1を返す(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 一度印刷したあと、発行者情報のほかに残ったファイルが壊れた状態。
    before = set(files(place.folder()))
    path = ledger(csv(*README_ROWS))
    terminal()
    assert command.main([str(path)]) == 0
    capsys.readouterr()
    records = [each for each in files(place.folder()) if each not in before]
    for each in records:
        each.write_bytes(b"\x00broken")
    printer.sent.clear()
    terminal()
    # When
    code = command.main([str(path)])
    # Then
    out = capsys.readouterr().out
    assert code == 1
    assert records != [] and any(str(each) in out for each in records)
    assert printer.sent == []


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
@pytest.mark.parametrize("problem", ["no_default_printer", "send_failed"])
def test_印刷を断られるとプリンターの整え方を示して1を返す(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    problem: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 既定のプリンターがないか、印刷システムが断るノートPC。
    printer.refuse_at, printer.problem = 0, problem
    terminal()
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 1
    assert "プリンター" in out
    assert "印刷しました" not in out
    assert printer.sent == []


class EndedInput(Terminal):
    """答えを順に返し、尽きると利用者が Ctrl+D を押したように空を返す、端末の入力の代役。"""

    def readline(self) -> str:
        return self.answers.pop(0) + "\n" if self.answers else ""


class Keyboard(Terminal):
    """利用者が打った答えを端末が画面に示す、本物の端末の入力の代役。"""

    def isatty(self) -> bool:
        return True


@supports("test_答えずに止めると何も残さず次は最初から尋ねる")
def test_尋ねる途中で入力が尽きると何も残さず130を返す(
    home: Path,
    ledger: Callable[..., Path],
    printer: Printer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 二つの事柄に答えたあと、Ctrl+D を押す利用者。
    monkeypatch.setattr(sys, "stdin", EndedInput(AOBA_ANSWERS[:2]))
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    assert code == 130
    assert asked(capsys.readouterr().out) == list(AOBA_LABELS[:3])
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_初回は事柄を順に尋ねすべての答えがそろってから残す")
def test_端末では利用者の打った答えを示し直さない(
    home: Path,
    ledger: Callable[..., Path],
    printer: Printer,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 本物の端末で答える利用者。
    monkeypatch.setattr(sys, "stdin", Keyboard(AOBA_ANSWERS))
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then: 事柄の名前は続けて示され、答えは端末が示すので invoice は示さない。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == list(AOBA_LABELS)
    assert "発行者の正式名称: 登録番号(T と 13 桁の数字): " in out
    assert "T1234567890123" not in out


@supports("test_形に合わない答えは例を示して同じ事柄を尋ね直す")
def test_空の答えには空だと示して同じ事柄を尋ね直す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 最初の事柄に、何も打たずに Enter を押してから答える利用者。
    terminal("", *AOBA_ANSWERS)
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == [AOBA_LABELS[0], *AOBA_LABELS]
    assert "答えが空です。たとえば「株式会社あおば事務用品」のように答えてください。" in out
    assert issuer.load() == AOBA


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_受け付けない値は行と列と値と決まりと例を一行で示す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 二行目の取引日に、ない日付を書いた明細。
    path = ledger(csv("株式会社みなと商事,2026-11-31,コピー用紙 A4 500枚,10,箱,2800,10%"))
    terminal()
    # When
    code = command.main([str(path)])
    # Then
    out = capsys.readouterr().out
    assert code == 1
    assert (
        f"- {path} の 2 行目、「取引日」の列: 「2026-11-31」は受け付けられません。"
        "取引日は 2026-11-20 か 2026/11/20 の形の、ある日付で書きます。たとえば「2026-11-20」と書きます。\n"
    ) in out
    assert "何も印刷していません。" in out


@supports("test_明細の直すところをすべて示し何も印刷しない")
def test_値のない列は値がないと示す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 二行目の数量が空の明細。
    path = ledger(csv("株式会社みなと商事,2026-11-05,コピー用紙 A4 500枚,,箱,2800,10%"))
    terminal()
    # When
    code = command.main([str(path)])
    # Then
    out = capsys.readouterr().out
    assert code == 1
    assert f"- {path} の 2 行目、「数量」の列: 値がありません。数量は、1 以上の整数で書きます。" in out


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行者情報のファイルを読めないとそのファイルと権限の直し方を示して1を返す(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報のファイルを読む権限がない状態。
    if os.geteuid() == 0:
        pytest.skip("root はどのファイルも読める")
    [path] = files(place.folder())
    path.chmod(0)
    terminal()
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 1
    assert f"chmod u+rw '{path}'" in out
    assert printer.sent == []


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_置き場に書けないと書けないことと直し方を示し何も残さず1を返す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: ホームフォルダーに書く権限がない状態で、初回の答えをすべて打つ利用者。
    if os.geteuid() == 0:
        pytest.skip("root はどこにでも書ける")
    path = ledger(csv(*README_ROWS))
    terminal(*AOBA_ANSWERS)
    home.chmod(0o500)
    try:
        # When
        code = command.main([str(path)])
    finally:
        home.chmod(0o700)
    # Then
    out = capsys.readouterr().out
    assert code == 1
    assert f"invoice: 発行者の情報と請求書番号を残すファイル {place.folder() / 'issuer.json'} で止まりました。" in out
    assert "書けません" in out
    assert files(place.folder()) == {}
    assert printer.sent == []
