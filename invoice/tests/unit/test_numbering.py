"""番号の採番 (numbering.number) の単体ケース。"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from invoice import numbering, place
from invoice.periods import Period
from tests.given import HIKARI, MINATO, MINATO_TOKYO, NOVEMBER, files

supports = pytest.mark.supports

OCTOBER = Period(date(2026, 10, 1), date(2026, 10, 31))
"""月末締めの、2026 年 10 月の締めの期間。"""


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_発行記録がない状態で初めての組には番号を付け発行記録に残す(home: Path) -> None:
    # Given: 発行記録のない状態。
    # When
    number = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    # Then
    assert number == "2026-11-001"
    assert files(place.folder()) != {}


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_初めての組には発行日の年月と年月ごとに001から数えた連番の番号を付ける(home: Path) -> None:
    # Given: 発行記録のない状態。
    # When: 11 月 30 日発行の二つの組、10 月 31 日発行の組、11 月 20 日発行の組、前の組の順に番号を求める。
    numbers = [
        numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end),
        numbering.number(HIKARI.name, NOVEMBER, NOVEMBER.end),
        numbering.number(MINATO.name, OCTOBER, OCTOBER.end),
        numbering.number(MINATO.name, Period(date(2026, 10, 21), date(2026, 11, 20)), date(2026, 11, 20)),
        numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end),
    ]
    # Then: 発行月ごとに 001 から数え、前に付けた組は数え直さない。
    assert numbers == ["2026-11-001", "2026-11-002", "2026-10-001", "2026-11-003", "2026-11-001"]


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
@pytest.mark.parametrize(
    ("issue_date", "expected"),
    [
        (date(2026, 12, 1), "2026-12-001"),
        (date(2026, 12, 31), "2026-12-001"),
        (date(2027, 1, 31), "2027-01-001"),
        (date(2026, 9, 30), "2026-09-001"),
    ],
)
def test_番号の年と月は発行日の年と2桁の月(home: Path, issue_date: date, expected: str) -> None:
    # Given: 発行記録のない状態と、月の初めか終わりか、年の変わり目か、一桁の月の発行日。
    period = Period(issue_date.replace(day=1), issue_date)
    # When
    number = numbering.number(MINATO.name, period, issue_date)
    # Then
    assert number == expected


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
def test_同じ月の十番目の組には3桁の連番010を付ける(home: Path) -> None:
    # Given: 11 月発行の九つの組に番号を付けた状態。
    before = [numbering.number(f"取引先 {i}", NOVEMBER, NOVEMBER.end) for i in range(1, 10)]
    # When
    tenth = numbering.number("取引先 10", NOVEMBER, NOVEMBER.end)
    # Then
    assert before[-1] == "2026-11-009"
    assert tenth == "2026-11-010"


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_前に付けた組にはいくつの組のあとでも前と同じ番号を返し発行記録を変えない(home: Path) -> None:
    # Given: 三つの組に番号を付けた状態。
    first = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    numbering.number(MINATO.name, OCTOBER, OCTOBER.end)
    numbering.number(HIKARI.name, NOVEMBER, NOVEMBER.end)
    kept = files(place.folder())
    # When
    again = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    # Then
    assert again == first
    assert files(place.folder()) == kept


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
@pytest.mark.parametrize(
    ("customer", "period"),
    [
        (HIKARI.name, NOVEMBER),
        (MINATO_TOKYO.name, NOVEMBER),
        ("株式会社みなと", NOVEMBER),
        (MINATO.name, OCTOBER),
        (MINATO.name, Period(date(2026, 10, 21), date(2026, 11, 20))),
        (MINATO.name, Period(date(2026, 11, 1), date(2026, 11, 29))),
    ],
)
def test_取引先か期間が違えば近い組にもほかの組に付けていない番号を付ける(
    home: Path, customer: str, period: Period
) -> None:
    # Given: みなと商事の 11 月分に番号を付けた状態。
    first = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    # When
    other = numbering.number(customer, period, period.end)
    # Then
    assert other != first
    assert numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end) == first


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行記録が壊れていれば壊れていると断り発行記録を前のまま残す(home: Path) -> None:
    # Given: 発行記録が壊れた状態。
    numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    for each in files(place.folder()):
        each.write_bytes(b"\x00broken")
    kept = files(place.folder())
    # When
    with pytest.raises(place.StoreRefused) as refused:
        numbering.number(MINATO.name, OCTOBER, OCTOBER.end)
    # Then
    assert refused.value.fix.problem == "broken"
    assert refused.value.fix.path in kept
    assert files(place.folder()) == kept


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
@pytest.mark.parametrize("content", ['"2026-11-001"', "1"])
def test_発行記録が読めても発行記録の形に合わなければ壊れていると断り前のまま残す(home: Path, content: str) -> None:
    # Given: 発行記録のファイルが、JSON としては読めるが、組と番号を持たない状態。
    numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    for each in files(place.folder()):
        each.write_text(content, encoding="utf-8")
    kept = files(place.folder())
    # When
    with pytest.raises(place.StoreRefused) as refused:
        numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    # Then
    assert refused.value.fix.problem == "broken"
    assert refused.value.fix.path in kept
    assert files(place.folder()) == kept


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
def test_書けない発行記録では前に付けた組には番号を返し初めての組は書けないと断る(home: Path) -> None:
    # Given: 一つの組に番号を付けたあと、置き場に書けなくなった状態。
    if os.geteuid() == 0:
        pytest.skip("root はどこにでも書ける")
    first = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
    kept = files(place.folder())
    locked = [place.folder(), *place.folder().rglob("*")]
    for each in locked:
        each.chmod(0o500 if each.is_dir() else 0o400)
    try:
        # When
        again = numbering.number(MINATO.name, NOVEMBER, NOVEMBER.end)
        with pytest.raises(place.StoreRefused) as refused:
            numbering.number(MINATO.name, OCTOBER, OCTOBER.end)
        # Then
        assert again == first
        assert refused.value.fix.problem == "unwritable"
        assert files(place.folder()) == kept
    finally:
        for each in locked:
            each.chmod(0o700 if each.is_dir() else 0o600)
