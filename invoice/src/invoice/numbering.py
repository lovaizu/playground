"""取引先と締めの期間の組に、どの請求書番号を付けるか。"""

from __future__ import annotations

import datetime
from typing import Any

from invoice import place
from invoice.periods import Period

_FILE = "numbers.json"
"""置き場の中の、発行記録のファイルの名前。"""


def number(customer_name: str, period: Period, issue_date: datetime.date) -> str:
    """番号を求める (S1)。

    受け取る: 請求書の取引先の名称と締めの期間と、periods.dates_of が決めた発行日。
        置き場の場所は place.folder から受け取る。
    返す: その組の請求書番号。前に付けた組には、前と同じ番号 (P3.5, P1.4)。
        初めての組には、ほかの組に付けていない番号。
        番号は「<発行年>-<発行月2桁>-<連番3桁>」の形で、例: `2026-11-001`。
        連番は発行日の月ごとに 001 から数え、その月に付けた番号の次とする。
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
    month = f"{issue_date.year}-{issue_date.month:02}-"
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
        return list(stored["records"])
    except (KeyError, TypeError) as error:
        raise place.broken(_FILE, f"発行記録の形に合わない: {error!r}") from error
