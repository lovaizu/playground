"""invoice が残すファイルを、ノートPCのどこに、どう書いて置くか。"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class StoreFix:
    """直すところ: 置き場のファイルの一つを読めない、または残せないわけ。

    コマンドはこの値だけから、どのファイルの何をどう直すかを日本語で示す。
    """

    path: Path
    """問題のファイル。"""
    problem: Literal["unreadable", "broken", "unwritable"]
    """読めない、中身が壊れている、または書けない。"""
    detail: str
    """ファイルシステムか読み取りが返したわけ。なければ空。"""


class StoreRefused(Exception):
    """置き場のファイルを読めない、または残せないときに上がり、直すところを持つ。"""

    def __init__(self, fix: StoreFix) -> None:
        super().__init__(fix)
        self.fix = fix


def folder() -> Path:
    """invoice の置き場のフォルダー。利用者のホームフォルダーの中にある (P2.2)。

    受け取る: なし。ホームフォルダーは環境変数 HOME から取る。
    返す: 置き場のフォルダーのパス。どのフォルダーで打っても同じパス。
    ほかに変えるもの: なし。フォルダーを作るのは write。
    断るとき: なし。
    """
    return Path.home() / ".local" / "share" / "invoice"


def read(name: str) -> Any | None:
    """置き場のファイルの一つを、JSON の値として読む。

    受け取る: 置き場の中のファイルの名前。例: `issuer.json`。
    返す: ファイルの中身の JSON の値。ファイルがなければ None。
    ほかに変えるもの: なし。
    断るとき:
        StoreRefused: 読む権限がないなど読めないとき (unreadable)、
            UTF-8 の JSON として読めないとき (broken)。
    """
    path = folder() / name
    try:
        text = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise StoreRefused(StoreFix(path, "unreadable", error.strerror or "")) from error
    try:
        return json.loads(text.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StoreRefused(StoreFix(path, "broken", str(error))) from error


def broken(name: str, detail: str) -> StoreRefused:
    """置き場のファイルの一つが、読めても形に合わないときの断り。

    受け取る: 置き場の中のファイルの名前と、形に合わないわけ。
    返す: そのファイルが壊れていると示す StoreRefused。上げるのは呼んだ側。
    ほかに変えるもの: なし。
    断るとき: なし。
    """
    return StoreRefused(StoreFix(folder() / name, "broken", detail))


def write(name: str, value: Any) -> None:
    """置き場のファイルの一つを、JSON の値で一度に書き替える。

    受け取る: 置き場の中のファイルの名前と、JSON にできる値。
    返す: なし。
    ほかに変えるもの: 置き場のフォルダーがなければ作り、ファイルを書き替える。
        書き替えは一度に起き、途中で止まっても前の中身か新しい中身のどちらかが残る。
    断るとき:
        StoreRefused: フォルダーかファイルを書けないとき (unwritable)。ファイルは前のまま。
    """
    path = folder() / name
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
            file.write(text)
        os.replace(file.name, path)
    except OSError as error:
        raise StoreRefused(StoreFix(path, "unwritable", error.strerror or "")) from error
