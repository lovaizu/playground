"""紙面を、ノートPCの印刷システムにどう届けるか。"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from invoice.layout import PrintDocument


@dataclass(frozen=True)
class PrintFix:
    """直すところ: 紙面が既定のプリンターに届かないわけ (S4)。"""

    problem: Literal["no_default_printer", "send_failed"]
    """既定のプリンターがない、または送れない。"""
    detail: str
    """印刷システムが返したわけ。なければ空。"""


class PrintRefused(Exception):
    """紙面を既定のプリンターに届けられないときに上がり、直すところを持つ。"""

    def __init__(self, fix: PrintFix) -> None:
        super().__init__(fix)
        self.fix = fix


@dataclass(frozen=True)
class Printed:
    """印刷を頼み終えた結果: どのプリンターに、何枚の用紙を送ったか (P2.6)。"""

    printer: str | None
    """送った既定のプリンターの名前。一つも送らなければ None。"""
    sheets: int
    """送った用紙の枚数。"""


_DEFAULT = re.compile(r"^system default destination: (\S+)$", re.M)
"""`lpstat -d` が既定のプリンターを示す行。"""


def print_documents(documents: Sequence[PrintDocument]) -> Printed:
    """印刷させる (S1, S4)。

    受け取る: 印刷用の文書。
    返す: 送った既定のプリンターの名前と、送った用紙の枚数 (P2.6)。
    ほかに変えるもの: 文書を受け取った順に、send で既定のプリンターに送る。
    断るとき:
        PrintRefused: 既定のプリンターがないとき、一つも送らずに上がる。
            途中で送れなくなったとき、そこで上がる (S4)。
    """
    printer = None
    for document in documents:
        printer = send(document)
    return Printed(printer=printer, sheets=sum(document.sheets for document in documents))


def send(document: PrintDocument) -> str:
    """既定のプリンターに送る (S1, S4)。印刷システムへの矢印を運ぶ。

    印刷システムに触れるのは、この関数だけ (P2.3)。テストでは代役に替える。
    受け取る: 一つの印刷用の文書。
    返す: 送った既定のプリンターの名前。`lpstat -d` が示すもの。
    ほかに変えるもの: 印刷システム (CUPS) に、`lp` で既定のプリンターでの印刷を頼む。
    断るとき:
        PrintRefused: 既定のプリンターがないとき、または `lpstat` がないとき (no_default_printer)。
            印刷システムが断ったとき (send_failed)。
    """
    environment = {**os.environ, "LC_ALL": "C"}
    try:
        asked = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, env=environment, check=False)
    except FileNotFoundError as error:
        raise PrintRefused(PrintFix("no_default_printer", str(error))) from error
    found = _DEFAULT.search(asked.stdout)
    if found is None:
        raise PrintRefused(PrintFix("no_default_printer", (asked.stdout + asked.stderr).strip()))
    printer = found[1]
    try:
        sent = subprocess.run(
            ["lp", "-d", printer, "-t", "請求書", "-"],
            input=document.pdf,
            capture_output=True,
            env=environment,
            check=False,
        )
    except FileNotFoundError as error:
        raise PrintRefused(PrintFix("send_failed", str(error))) from error
    if sent.returncode != 0:
        raise PrintRefused(PrintFix("send_failed", sent.stderr.decode("utf-8", "replace").strip()))
    return printer
