"""発行者情報の保管 (issuer.load, issuer.check, issuer.save) の単体ケース。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from invoice import issuer, place
from invoice.issuer import AnswerFix, IssuerItem, PaymentTerms
from tests.given import AOBA, AOBA_LABELS, ITEMS, checked, files, save_aoba

supports = pytest.mark.supports


@supports("test_初回は事柄を順に尋ねすべての答えがそろってから残す")
def test_残していなければ尋ねる事柄をガイドの順と名前で返し例はそのまま受け付けられる(home: Path) -> None:
    # Given: 何も残していない状態。
    # When
    questions = issuer.load()
    # Then
    assert isinstance(questions, tuple)
    assert [(question.item, question.label) for question in questions] == list(zip(ITEMS, AOBA_LABELS, strict=True))
    for question in questions:
        issuer.check(question.item, question.example)
    assert files(place.folder()) == {}


@supports("test_二回目からは何も尋ねずに印刷まで進む")
def test_残したあとは残した発行者情報を返す(home: Path) -> None:
    # Given: 発行者情報を残した状態。
    saved = save_aoba()
    # When
    loaded = issuer.load()
    # Then
    assert loaded == saved == AOBA


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行者情報のファイルが壊れていれば壊れていると断る(home: Path) -> None:
    # Given: 発行者情報のファイルが壊れた状態。
    save_aoba()
    broken = list(files(place.folder()))
    for each in broken:
        each.write_bytes(b"\x00broken")
    # When
    with pytest.raises(place.StoreRefused) as refused:
        issuer.load()
    # Then
    assert refused.value.fix.problem == "broken"
    assert refused.value.fix.path in broken


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
@pytest.mark.parametrize("content", ["{}", "[]", '"株式会社あおば事務用品"'])
def test_発行者情報のファイルが読めても発行者情報の形に合わなければ壊れていると断る(home: Path, content: str) -> None:
    # Given: 発行者情報のファイルが、JSON としては読めるが、八つの事柄を持たない状態。
    save_aoba()
    broken = list(files(place.folder()))
    for each in broken:
        each.write_text(content, encoding="utf-8")
    # When
    with pytest.raises(place.StoreRefused) as refused:
        issuer.load()
    # Then
    assert refused.value.fix.problem == "broken"
    assert refused.value.fix.path in broken


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行者情報のファイルが読めなければ読めないと断る(home: Path) -> None:
    # Given: 発行者情報のファイルを読む権限がない状態。
    if os.geteuid() == 0:
        pytest.skip("root はどのファイルも読める")
    save_aoba()
    locked = list(files(place.folder()))
    for each in locked:
        each.chmod(0)
    # When
    with pytest.raises(place.StoreRefused) as refused:
        issuer.load()
    # Then
    assert refused.value.fix.problem == "unreadable"
    assert refused.value.fix.path in locked


@supports("test_初回は事柄を順に尋ねすべての答えがそろってから残す")
@pytest.mark.parametrize(
    ("item", "answer", "expected"),
    [
        ("name", "株式会社あおば事務用品", "株式会社あおば事務用品"),
        ("registration_number", "T1234567890123", "T1234567890123"),
        ("bank_name", "さくら銀行", "さくら銀行"),
        ("bank_branch", "本店営業部", "本店営業部"),
        ("account_type", "普通", "普通"),
        ("account_type", "当座", "当座"),
        ("account_number", "1234567", "1234567"),
        ("account_number", "0000000", "0000000"),
        ("account_holder", "カ)アオバジムヨウヒン", "カ)アオバジムヨウヒン"),
        ("registration_number", "Ｔ１２３４５６７８９０１２３", "T1234567890123"),
        ("account_number", "１２３４５６７", "1234567"),
        ("account_holder", "ｶ)ｱｵﾊﾞｼﾞﾑﾖｳﾋﾝ", "カ)アオバジムヨウヒン"),
    ],
)
def test_形に合う答えは全角の英数字を半角に半角カナを全角に読み替えて返し何も残さない(
    home: Path, item: IssuerItem, answer: str, expected: str
) -> None:
    # Given: 何も残していない状態。
    # When
    result = issuer.check(item, answer)
    # Then
    assert result == expected
    assert files(place.folder()) == {}


@supports("test_支払条件は三つの値で保たれ期間と期限はその値から決まる")
@pytest.mark.parametrize(
    ("answer", "terms"),
    [
        ("20日締め翌月10日払い", PaymentTerms(20, 1, 10)),
        ("月末締め翌月末払い", PaymentTerms("month_end", 1, "month_end")),
        ("月末締め翌月10日払い", PaymentTerms("month_end", 1, 10)),
        ("20日締め翌々月10日払い", PaymentTerms(20, 2, 10)),
        ("10日締め当月25日払い", PaymentTerms(10, 0, 25)),
        ("27日締め当月28日払い", PaymentTerms(27, 0, 28)),
        ("27日締め当月末払い", PaymentTerms(27, 0, "month_end")),
        ("1日締め翌月1日払い", PaymentTerms(1, 1, 1)),
        ("28日締め翌月28日払い", PaymentTerms(28, 1, 28)),
        ("２０日締め翌月１０日払い", PaymentTerms(20, 1, 10)),
    ],
)
def test_形どおりの支払条件は締め日と支払の月と支払日に読み取る(home: Path, answer: str, terms: PaymentTerms) -> None:
    # Given: 何も残していない状態。
    # When
    result = issuer.check("payment_terms", answer)
    # Then
    assert result == terms
    assert files(place.folder()) == {}


@supports("test_形に合わない答えは例を示して同じ事柄を尋ね直す")
@pytest.mark.parametrize(
    ("item", "answer"),
    [
        *[(item, "") for item in ITEMS],
        ("registration_number", "T123456789012"),
        ("registration_number", "T12345678901234"),
        ("registration_number", "1234567890123"),
        ("registration_number", "TT234567890123"),
        ("payment_terms", "20日締め翌月10日"),
        ("payment_terms", "20日〆翌月10日払い"),
        ("payment_terms", "20日締め翌翌月10日払い"),
        ("payment_terms", "0日締め翌月10日払い"),
        ("payment_terms", "29日締め翌月10日払い"),
        ("payment_terms", "20日締め翌月29日払い"),
        ("payment_terms", "20日締め当月20日払い"),
        ("payment_terms", "20日締め当月10日払い"),
        ("payment_terms", "月末締め当月末払い"),
        ("payment_terms", "月末締め当月10日払い"),
        ("account_type", "貯蓄"),
        ("account_number", "123456"),
        ("account_number", "12345678"),
        ("account_number", "123456a"),
        ("account_holder", "株式会社あおば事務用品"),
        ("account_holder", "aoba"),
    ],
)
def test_形に合わない答えはその事柄と答えと受け付ける例で断り何も残さない(
    home: Path, item: IssuerItem, answer: str
) -> None:
    # Given: 何も残していない状態。
    # When
    with pytest.raises(issuer.AnswerRefused) as refused:
        issuer.check(item, answer)
    # Then
    fix = refused.value.fix
    assert (fix.item, fix.given) == (item, answer)
    assert isinstance(fix, AnswerFix)
    issuer.check(item, fix.expected)
    assert files(place.folder()) == {}


@supports("test_初回は事柄を順に尋ねすべての答えがそろってから残す")
def test_すべての答えをそろえて残させると発行者情報を返し次に読める(home: Path) -> None:
    # Given: 何も残していない状態。
    # When
    saved = issuer.save(checked())
    # Then
    assert saved == AOBA
    assert issuer.load() == AOBA


@supports("test_答えずに止めると何も残さず次は最初から尋ねる")
@pytest.mark.parametrize("missing", [ITEMS, ("account_holder",), ("name", "payment_terms")])
def test_答えが欠けていれば欠けた事柄を順に持って断り何も残さない(home: Path, missing: tuple[IssuerItem, ...]) -> None:
    # Given: 事柄の一つ、いくつか、またはすべてが欠けた答え。
    answers = {item: answer for item, answer in checked().items() if item not in missing}
    # When
    with pytest.raises(issuer.AnswersIncomplete) as refused:
        issuer.save(answers)
    # Then
    assert refused.value.missing == missing
    assert isinstance(issuer.load(), tuple)
    assert files(place.folder()) == {}


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_書けない置き場には書けないと断り何も残さない(home: Path) -> None:
    # Given: ホームフォルダーに書く権限がない状態。
    if os.geteuid() == 0:
        pytest.skip("root はどこにでも書ける")
    home.chmod(0o500)
    try:
        # When
        with pytest.raises(place.StoreRefused) as refused:
            issuer.save(checked())
        # Then
        assert refused.value.fix.problem == "unwritable"
        assert refused.value.fix.path.is_relative_to(home)
        assert files(place.folder()) == {}
    finally:
        home.chmod(0o700)
