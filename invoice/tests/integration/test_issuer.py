"""S3: 発行者の情報を一度だけ伝える道筋と、その原則と決めごとの結合ケース。"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import command, issuer, periods, place
from invoice.issuer import Issuer, PaymentTerms
from tests.given import (
    AOBA,
    AOBA_ANSWERS,
    AOBA_LABELS,
    README_ROWS,
    Printer,
    Terminal,
    asked,
    csv,
    files,
    paper,
)

supports = pytest.mark.supports


def refusal(item: issuer.IssuerItem, answer: str) -> issuer.AnswerFix:
    """答えを確かめさせたときの、直すところ。"""
    with pytest.raises(issuer.AnswerRefused) as refused:
        issuer.check(item, answer)
    return refused.value.fix


@supports("S3", "P2.1", "P2.4", "発行者情報", "発行者情報の保管")
def test_初回は事柄を順に尋ねすべての答えがそろってから残す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、ガイドの明細。
    path = ledger(csv(*README_ROWS))
    terminal(*AOBA_ANSWERS)
    # When: 利用者が明細のファイルを渡し、尋ねられた事柄に答える。
    code = command.main([str(path)])
    # Then: 事柄を一度ずつ順に尋ね、答えを発行者情報として残し、印刷まで進む。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == list(AOBA_LABELS)
    assert issuer.load() == AOBA
    assert len(printer.sent) == 1


@supports("S3", "P2.5")
def test_明細に直すところがあれば初回も何も尋ねずに止まる(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報をまだ残していないノートPCと、取引日に誤りのある明細。
    path = ledger(csv("株式会社みなと商事,2026-11-31,コピー用紙 A4 500枚,10,箱,2800,10%"))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 何も尋ねず、何も残さず、何も印刷せずに止まる。
    out = capsys.readouterr().out
    assert code == 1
    assert asked(out) == []
    assert "2026-11-31" in out
    assert isinstance(issuer.load(), tuple)
    assert files(place.folder()) == {}
    assert printer.sent == []


@supports("S3", "P2.4")
def test_答えずに止めると何も残さず次は最初から尋ねる(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 初回に、三つの事柄に答えたあと、四つ目で利用者が Ctrl+C で止める。
    path = ledger(csv(*README_ROWS))
    terminal(*AOBA_ANSWERS[:3])
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 130 で止まり、発行者情報を何も残さず、何も印刷しない。
    out = capsys.readouterr().out
    assert code == 130
    assert asked(out) == list(AOBA_LABELS[:4])
    assert files(place.folder()) == {}
    assert printer.sent == []
    # When: 利用者がもう一度打つ。
    terminal(*AOBA_ANSWERS)
    again = command.main([str(path)])
    # Then: 初回として最初の事柄から尋ね直す。
    assert again == 0
    assert asked(capsys.readouterr().out) == list(AOBA_LABELS)


@supports("S3", "P1.5", "P3.10", "P3.11", "P3.12", "直すところ")
def test_形に合わない答えは例を示して同じ事柄を尋ね直す(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 支払条件に、形に合わない答えを三つ続けてから、正しい答えを打つ利用者。
    wrong = ("月末締め当月末払い", "29日締め翌月10日払い", "20日締め翌月10日")
    path = ledger(csv(*README_ROWS))
    terminal(*AOBA_ANSWERS[:2], *wrong, *AOBA_ANSWERS[2:])
    # When: 利用者が明細のファイルを渡し、尋ねられた事柄に答える。
    code = command.main([str(path)])
    # Then: 答えごとに受け付ける形の例を示し、支払条件だけを尋ね直して、正しい答えを残す。
    out = capsys.readouterr().out
    assert code == 0
    assert asked(out) == [*AOBA_LABELS[:2], *[AOBA_LABELS[2]] * 4, *AOBA_LABELS[3:]]
    for answer in wrong:
        assert refusal("payment_terms", answer).expected in out
    assert issuer.load() == AOBA


@supports("S3", "P2.2")
def test_二回目からは何も尋ねずに印刷まで進む(
    aoba: Issuer,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 発行者情報を残したあと。
    path = ledger(csv(*README_ROWS))
    terminal()
    # When: 利用者が明細のファイルを渡す。
    code = command.main([str(path)])
    # Then: 何も尋ねずに印刷まで進む。
    assert code == 0
    assert asked(capsys.readouterr().out) == []
    assert len(printer.sent) == 1


@supports("S3", "P3.9", "P3.10", "発行者情報の保管", "請求の計算")
def test_支払条件は三つの値で保たれ期間と期限はその値から決まる(
    home: Path,
    ledger: Callable[..., Path],
    terminal: Callable[..., Terminal],
    printer: Printer,
) -> None:
    # Given: 初回に、支払条件を「20日締め翌月10日払い」と答える利用者。
    answers = (*AOBA_ANSWERS[:2], "20日締め翌月10日払い", *AOBA_ANSWERS[3:])
    terminal(*answers)
    # When: 利用者がガイドの明細を渡す。
    code = command.main([str(ledger(csv(*README_ROWS)))])
    # Then: 支払条件は三つの値で残り、請求書の日付はその値から決まる。
    terms = PaymentTerms(closing_day=20, month=1, payment_day=10)
    loaded = issuer.load()
    assert code == 0
    assert isinstance(loaded, Issuer) and loaded.payment_terms == terms
    text = paper(printer.sent[0])
    assert "発行日: 2026年11月20日" in text
    assert "お支払期限: 2026年12月10日" in text
    day, read = datetime.date(2026, 11, 5), issuer.check("payment_terms", answers[2])
    assert isinstance(read, PaymentTerms)
    assert periods.dates_of(day, read) == periods.dates_of(day, terms)
