"""番号の採番 (numbering.number) の単体ケース。"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest

from invoice import numbering, place
from invoice.periods import Period
from tests.given import files

supports = pytest.mark.supports

OCTOBER = Period(date(2026, 10, 1), date(2026, 10, 31))
NOVEMBER = Period(date(2026, 11, 1), date(2026, 11, 30))
MINATO = "株式会社みなと商事"


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_発行記録がない状態で初めての組には番号を付け発行記録に残す(home: Path) -> None:
    # Given: 発行記録のない状態。
    # When
    number = numbering.number(MINATO, NOVEMBER)
    # Then
    assert number != ""
    assert files(place.folder()) != {}


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_前に付けた組にはいくつの組のあとでも前と同じ番号を返し発行記録を変えない(home: Path) -> None:
    # Given: 三つの組に番号を付けた状態。
    first = numbering.number(MINATO, NOVEMBER)
    numbering.number(MINATO, OCTOBER)
    numbering.number("株式会社ひかり設計", NOVEMBER)
    kept = files(place.folder())
    # When
    again = numbering.number(MINATO, NOVEMBER)
    # Then
    assert again == first
    assert files(place.folder()) == kept


@supports("test_取引先と締めの期間ごとに一枚ずつ印刷される")
@pytest.mark.parametrize(
    ("customer", "period"),
    [
        ("株式会社ひかり設計", NOVEMBER),
        ("株式会社みなと商事東京支店", NOVEMBER),
        ("株式会社みなと", NOVEMBER),
        (MINATO, OCTOBER),
        (MINATO, Period(date(2026, 10, 21), date(2026, 11, 20))),
        (MINATO, Period(date(2026, 11, 1), date(2026, 11, 29))),
    ],
)
def test_取引先か期間が違えば近い組にもほかの組に付けていない番号を付ける(
    home: Path, customer: str, period: Period
) -> None:
    # Given: みなと商事の 11 月分に番号を付けた状態。
    first = numbering.number(MINATO, NOVEMBER)
    # When
    other = numbering.number(customer, period)
    # Then
    assert other != first
    assert numbering.number(MINATO, NOVEMBER) == first


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
def test_発行記録が壊れていれば壊れていると断り発行記録を前のまま残す(home: Path) -> None:
    # Given: 発行記録が壊れた状態。
    numbering.number(MINATO, NOVEMBER)
    for each in files(place.folder()):
        each.write_bytes(b"\x00broken")
    kept = files(place.folder())
    # When
    with pytest.raises(place.StoreRefused) as refused:
        numbering.number(MINATO, OCTOBER)
    # Then
    assert refused.value.fix.problem == "broken"
    assert refused.value.fix.path in kept
    assert files(place.folder()) == kept


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
def test_書けない発行記録では前に付けた組には番号を返し初めての組は書けないと断る(home: Path) -> None:
    # Given: 一つの組に番号を付けたあと、置き場に書けなくなった状態。
    if os.geteuid() == 0:
        pytest.skip("root はどこにでも書ける")
    first = numbering.number(MINATO, NOVEMBER)
    kept = files(place.folder())
    locked = [place.folder(), *[each for each in place.folder().rglob("*")]]
    for each in locked:
        each.chmod(0o500 if each.is_dir() else 0o400)
    try:
        # When
        again = numbering.number(MINATO, NOVEMBER)
        with pytest.raises(place.StoreRefused) as refused:
            numbering.number(MINATO, OCTOBER)
        # Then
        assert again == first
        assert refused.value.fix.problem == "unwritable"
        assert files(place.folder()) == kept
    finally:
        for each in locked:
            each.chmod(0o700 if each.is_dir() else 0o600)


@supports("test_同じ明細を二度印刷しても同じ請求書番号になる")
def test_初めての組には締め日の年月と年月ごとに001から数えた連番の番号を付ける(home: Path) -> None:
    # Given: 発行記録のない状態。
    # When: 11 月締めの二つの組、10 月締めの組、11 月 20 日締めの組の順に番号を求める。
    numbers = [
        numbering.number(MINATO, NOVEMBER),
        numbering.number("株式会社ひかり設計", NOVEMBER),
        numbering.number(MINATO, OCTOBER),
        numbering.number(MINATO, Period(date(2026, 10, 21), date(2026, 11, 20))),
    ]
    # Then
    assert numbers == ["2026-11-001", "2026-11-002", "2026-10-001", "2026-11-003"]


@supports("test_置き場のファイルが壊れていると直し方を示し何も印刷しない")
@pytest.mark.parametrize(
    "content",
    [
        {"version": 1},
        {
            "version": 1,
            "records": [{"customer": 1, "start": "2026-11-01", "end": "2026-11-30", "number": "2026-11-001"}],
        },
        {
            "version": 1,
            "records": [{"customer": MINATO, "start": "11月", "end": "2026-11-30", "number": "2026-11-001"}],
        },
        {"version": 1, "records": [{"customer": MINATO, "start": "2026-11-01", "end": "2026-11-30", "number": 1}]},
    ],
)
def test_発行記録が読めても残したときの形に合わなければ壊れていると断り前のまま残す(
    home: Path, content: object
) -> None:
    # Given: 発行記録のファイルが、JSON としては読めるが、残したときの形でない状態。
    numbering.number(MINATO, NOVEMBER)
    [path] = files(place.folder())
    path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    kept = files(place.folder())
    # When
    with pytest.raises(place.StoreRefused) as refused:
        numbering.number(MINATO, NOVEMBER)
    # Then
    assert (refused.value.fix.path, refused.value.fix.problem) == (path, "broken")
    assert files(place.folder()) == kept
