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
    ASKED,
    DATE_RULE,
    FIRST_TIME,
    ITEMS,
    LEDGER_STOPPED,
    NO_PRINTER,
    QUANTITY_RULE,
    README_ROWS,
    README_SHEETS,
    Printer,
    Terminal,
    bad_value,
    bill_line,
    checked,
    csv,
    files,
    paper,
    printed,
    prompts,
    send_failed,
    store_stopped,
)

supports = pytest.mark.supports

USAGE = "使い方: invoice <明細のファイル.csv>\n       invoice --version\n"
"""引数が違うとき、端末のエラー出力に示す使い方。"""

README_SHOWN = bill_line("株式会社みなと商事 御中", "2026-11-001", "51,980") + printed(1) + "\n"
"""ガイドの明細を印刷したあと、端末に示す請求書の行と枚数の行。"""


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
def test_引数を渡さずに呼ぶとコマンドラインの引数を使う(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: 利用者が端末で `invoice --version` と打った状態。
    monkeypatch.setattr(sys, "argv", ["invoice", "--version"])
    # When
    code = command.main()
    # Then
    assert code == 0
    assert capsys.readouterr() == ("invoice 0.1.0\n", "")
    assert files(place.folder()) == {}


@supports("test_版を尋ねると版が示される")
@pytest.mark.parametrize("argv", [[], ["2026年11月分明細.csv", "2026年12月分明細.csv"], ["--version", "x.csv"]])
def test_引数が明細一つでも版でもなければ使い方を示して2を返す(
    home: Path, printer: Printer, argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: 何も残していないノートPC。
    # When
    code = command.main(argv)
    # Then
    assert code == 2
    assert capsys.readouterr() == ("", USAGE)
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
    assert capsys.readouterr().out == LEDGER_STOPPED + (
        f"- {missing}: このファイルが見つかりません。ファイルの名前と、端末を開いたフォルダーを確かめてください。"
        "明細を保存したフォルダーで「端末で開く」を選ぶと、ファイルの名前だけで渡せます。\n"
    )
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
    [fix] = refused.value.fixes
    assert fix.problem == "unreadable"
    assert code == 1
    assert out == LEDGER_STOPPED + (
        f"- {path}: このファイルを、UTF-8 の CSV として読めません ({fix.detail})。"
        "表計算ソフトで明細を開き、「ファイル」→「名前を付けて保存」で、"
        "種類を「テキスト CSV (.csv)」、文字セットを「Unicode (UTF-8)」にして保存し直してください。\n"
    )
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
    assert fix.expected != ""
    assert code == 1
    assert out == LEDGER_STOPPED + (
        f"- {path}: 見出しの行のほかに、明細の行がありません。見出しの下に、たとえば次の行を書き足してください。\n"
        f"  {fix.expected}\n"
    )
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_明細の直すところをすべて示し何も印刷しない")
@pytest.mark.parametrize(
    ("wrong", "column", "given", "rule", "example"),
    [
        (
            "株式会社みなと商事,2026-11-31,コピー用紙 A4 500枚,10,箱,2800,10%",
            "取引日",
            "2026-11-31",
            DATE_RULE,
            "2026-11-20",
        ),
        ("株式会社みなと商事,2026-11-05,コピー用紙 A4 500枚,,箱,2800,10%", "数量", None, QUANTITY_RULE, "10"),
    ],
)
def test_受け付けない値の行がある明細ではその行と列と値と受け付ける例を示し何も尋ねずに1を返す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    wrong: str,
    column: str,
    given: str | None,
    rule: str,
    example: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、二行目の取引日にない日付を書いたか、数量を空にした明細。
    path = ledger(csv(wrong))
    with pytest.raises(ledger_module.LedgerRefused) as refused:
        ledger_module.read(path)
    [fix] = refused.value.fixes
    terminal()
    # When
    code = command.main([str(path)])
    # Then: その行と列と、書かれていた値と、受け付ける形の例を示し、何も尋ねず、何も残さず、何も印刷しない。
    out = capsys.readouterr().out
    assert (fix.problem, fix.line, fix.column, fix.given, fix.expected) == ("bad_value", 2, column, given, example)
    assert code == 1
    assert out == LEDGER_STOPPED + bad_value(path, 2, column, given, rule, example)
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
    assert [question.label for question in questions] == list(AOBA_LABELS)
    assert out == ASKED + README_SHOWN
    assert issuer.load() == AOBA
    [document] = printer.sent
    assert paper(document) in README_SHEETS


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
    assert out == README_SHOWN
    assert issuer.load() == AOBA
    [document] = printer.sent
    assert paper(document) in README_SHEETS


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
    assert capsys.readouterr().out == FIRST_TIME + prompts(*AOBA_LABELS[: answered + 1]) + (
        "\ninvoice: 止めました。発行者の情報は何も残していません。次に打ったときに、初めから伺います。\n"
    )
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("test_形に合わない答えは例を示して同じ事柄を尋ね直す")
@pytest.mark.parametrize(
    ("at", "wrong", "said"),
    [
        (
            6,
            "123456",
            "「123456」は受け付けられません。7 桁の数字で答えてください。たとえば「1234567」のように答えてください。",
        ),
        (0, "", "答えが空です。たとえば「株式会社あおば事務用品」のように答えてください。"),
    ],
)
def test_断られた答えのあとは同じ事柄だけを尋ね直す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    at: int,
    wrong: str,
    said: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 口座番号に 6 桁を答えるか、名称に何も打たずに Enter を押してから、正しく答える利用者。
    terminal(*AOBA_ANSWERS[:at], wrong, *AOBA_ANSWERS[at:])
    with pytest.raises(issuer.AnswerRefused) as refused:
        issuer.check(ITEMS[at], wrong)
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then
    out = capsys.readouterr().out
    assert code == 0
    assert out == (
        FIRST_TIME + prompts(*AOBA_LABELS[: at + 1]) + said + "\n" + prompts(*AOBA_LABELS[at:]) + "\n" + README_SHOWN
    )
    assert refused.value.fix.expected in said
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
    [record] = records
    assert out == store_stopped(record) + (
        "このファイルの中身が壊れていて、読めません。"
        "バックアップがあれば戻してから、同じコマンドを打ち直してください。"
        "戻せないときは、この画面の文を貼って https://github.com/lovaizu/playground/issues で尋ねてください。\n"
    )
    assert printer.sent == []


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行者情報のファイルを読めないとそのファイルを示し何も尋ねず何も印刷せずに1を返す(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報を残したあと、そのファイルを読む権限がなくなった状態。
    if os.geteuid() == 0:
        pytest.skip("root はどのファイルも読める")
    locked = list(files(place.folder()))
    for each in locked:
        each.chmod(0)
    with pytest.raises(place.StoreRefused) as refused:
        issuer.load()
    terminal()
    # When
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then: 読めないファイルを示し、何も尋ねず、何も印刷せずに止まる。
    out = capsys.readouterr().out
    fix = refused.value.fix
    assert fix.problem == "unreadable"
    assert code == 1
    assert out == store_stopped(fix.path) + (
        f"このファイルを読む権限がありません ({fix.detail})。端末で次を打ってから、同じコマンドを打ち直してください。\n"
        f"  chmod u+rw '{fix.path}'\n"
    )
    assert printer.sent == []


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_置き場に書けないと書けないことと直し方を示し何も残さず1を返す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: ホームフォルダーに書く権限がない、初めてのノートPCと、初回の答えをすべて打つ利用者。
    if os.geteuid() == 0:
        pytest.skip("root はどこにでも書ける")
    path = ledger(csv(*README_ROWS))
    home.chmod(0o500)
    try:
        with pytest.raises(place.StoreRefused) as refused:
            issuer.save(checked())
        terminal(*AOBA_ANSWERS)
        # When
        code = command.main([str(path)])
        # Then: すべての事柄を尋ねたあと、書けないファイルを示し、何も残さず、何も印刷せずに止まる。
        out = capsys.readouterr().out
        fix = refused.value.fix
        assert fix.problem == "unwritable"
        assert code == 1
        assert out == ASKED + store_stopped(fix.path) + (
            f"このファイルを書けません ({fix.detail})。ホームフォルダーの空きと権限を確かめ、"
            "端末で次を打ってから、同じコマンドを打ち直してください。\n"
            f"  mkdir -p '{fix.path.parent}' && chmod u+rwx '{fix.path.parent}'\n"
        )
        assert files(place.folder()) == {}
        assert printer.sent == []
    finally:
        home.chmod(0o700)


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
@pytest.mark.parametrize(
    ("problem", "shown"), [("no_default_printer", NO_PRINTER), ("send_failed", send_failed("代役が断った"))]
)
def test_印刷を断られるとプリンターの整え方を示して1を返す(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    problem: str,
    shown: str,
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
    assert out == shown
    assert printer.sent == []
    assert issuer.load() == AOBA
