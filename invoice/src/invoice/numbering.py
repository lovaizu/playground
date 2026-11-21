"""取引先と締めの期間の組に、どの請求書番号を付けるか。"""

from __future__ import annotations

import datetime
from typing import Any

from invoice import place
from invoice.periods import Period

_FILE = "numbers.json"
"""置き場の中の、発行記録のファイルの名前。"""


def number(customer_name: str, period: Period) -> str:
    """番号を求める (S1)。

    受け取る: 請求書の取引先の名称と締めの期間。置き場の場所は place.folder から受け取る。
    返す: その組の請求書番号。前に付けた組には、前と同じ番号 (P3.5, P1.4)。
        初めての組には、「<発行年>-<発行月2桁>-<連番3桁>」の番号。例: `2026-11-001`。
        発行年月は締めの期間の締め日の年月で、連番はその年月に付けた番号の数に 1 を足したもの。
        連番は年月ごとに 001 から数え、ほかの組に付けていない番号になる。
    ほかに変えるもの: 初めての組なら、その番号を発行記録に残してから返す。
        発行記録を読み書きするのは、このモジュールだけ (P3.5)。
    断るとき:
        place.StoreRefused: 発行記録のファイルが読めない、壊れている、
            または書けないとき。発行記録は前のまま残す。
    """
    records = _records()
    key = {"customer": customer_name, "start": period.start.isoformat(), "end": period.end.isoformat()}
    for record in records:
        if {name: record[name] for name in key} == key:
            return str(record["number"])
    month = f"{period.end.year}-{period.end.month:02}-"
    count = sum(1 for record in records if str(record["number"]).startswith(month))
    found = f"{month}{count + 1:03}"
    place.write(_FILE, {"version": 1, "records": [*records, {**key, "number": found}]})
    return found


def _records() -> list[dict[str, Any]]:
    """発行記録の、付けた番号の記録を、付けた順に。発行記録がなければ空。"""
    stored = place.read(_FILE)
    if stored is None:
        return []
    try:
        records = stored["records"]
        for record in records:
            datetime.date.fromisoformat(record["start"])
            datetime.date.fromisoformat(record["end"])
            if not isinstance(record["customer"], str) or not isinstance(record["number"], str):
                raise TypeError(record)
    except (KeyError, TypeError, ValueError) as error:
        raise place.broken(_FILE, f"発行記録の形に合わない: {error!r}") from error
    return list(records)
