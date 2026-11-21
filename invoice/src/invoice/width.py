"""全角と半角の入り混じった入力を、確かめる前にどの字に読み替えるか。"""

from __future__ import annotations

import re
import unicodedata

_WIDE_OR_NARROW = re.compile("[！-～｡-ﾟ]+")
"""全角の数字・英字・記号 (U+FF01 から U+FF5E) と、半角カナ (U+FF61 から U+FF9F) の並び。"""


def narrowed(text: str) -> str:
    """明細の値や発行者の答えを、確かめる前の字にそろえたもの。

    受け取る: 利用者が書いた、または答えた文字列。
    返す: 全角の数字・英字・記号を半角に、半角カナを全角に読み替えた文字列。
        半角カナの濁点と半濁点は、前の字と一つの全角の字にする。例: `ﾊﾞ` は `バ`。
        ほかの字は、そのまま。
    ほかに変えるもの: なし。
    断るとき: なし。
    """
    return _WIDE_OR_NARROW.sub(lambda found: unicodedata.normalize("NFKC", found.group()), text)
