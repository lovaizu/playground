"""印刷 (printing.print_documents, printing.send) の単体ケース。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from invoice import layout, printing
from invoice.layout import PrintDocument
from invoice.printing import Printed
from tests.given import README_INVOICE, Printer

supports = pytest.mark.supports


def documents(*sheets: int) -> list[PrintDocument]:
    return [PrintDocument(pdf=b"%PDF-" + bytes([i]), sheets=count) for i, count in enumerate(sheets)]


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
@pytest.mark.parametrize(("sheets", "name"), [((), None), ((2,), "経理室プリンター"), ((1, 3, 1), "経理室プリンター")])
def test_紙面を受け取った順に送り既定のプリンターの名前と送った用紙の枚数を返す(
    printer: Printer, sheets: tuple[int, ...], name: str | None
) -> None:
    # Given: 紙面がない、一つ、またはいくつか。
    given = documents(*sheets)
    # When
    sent = printing.print_documents(given)
    # Then
    assert sent == Printed(printer=name, sheets=sum(sheets))
    assert printer.sent == given


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
def test_既定のプリンターがなければ一つも送らずに断る(printer: Printer) -> None:
    # Given
    printer.refuse_at, printer.problem = 0, "no_default_printer"
    # When
    with pytest.raises(printing.PrintRefused) as refused:
        printing.print_documents(documents(1, 1))
    # Then
    assert refused.value.fix.problem == "no_default_printer"
    assert printer.sent == []


@supports("test_送る途中で送れなくなると整え方を示して止まる")
def test_途中で送れなくなればそこで断りあとの紙面は送らない(printer: Printer) -> None:
    # Given
    printer.refuse_at = 1
    given = documents(1, 2, 1)
    # When
    with pytest.raises(printing.PrintRefused) as refused:
        printing.print_documents(given)
    # Then
    assert refused.value.fix.problem == "send_failed"
    assert printer.sent == given[:1]


@pytest.mark.host
@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_本物の印刷システムは既定のプリンターへの印刷を受け付ける() -> None:
    # Given: 既定のプリンターのある印刷システムと、ガイドの請求書の紙面。
    [document] = layout.typeset([README_INVOICE])
    # When
    printing.send(document)
    # Then: 印刷システムが断らずに受け付け、PrintRefused が上がらない。


def tool(bin_folder: Path, name: str, code: str) -> None:
    """bin_folder に、Python の code を走らせるコマンド name を置く。

    shebang の長さの上限にかからないよう、/bin/sh から Python を呼ぶ。
    """
    (bin_folder / f"{name}.py").write_text(code, encoding="utf-8")
    command = bin_folder / name
    command.write_text(f"#!/bin/sh\nexec '{sys.executable}' '{bin_folder / name}.py' \"$@\"\n", encoding="utf-8")
    command.chmod(0o755)


def system(folder: Path, monkeypatch: pytest.MonkeyPatch, default: str | None, lp_code: int | None) -> Path:
    """lpstat と lp の代役を置いた PATH。lp は受け取った引数と紙面を、folder の中に残す。

    default が None なら lpstat は既定のプリンターがないと示し、lp_code が None なら lp を置かない。
    """
    bin_folder = folder / "bin"
    bin_folder.mkdir()
    shown = f"system default destination: {default}" if default else "no system default destination"
    tool(bin_folder, "lpstat", f"import sys\nprint({shown!r})\nsys.exit({0 if default else 1})\n")
    if lp_code is not None:
        tool(
            bin_folder,
            "lp",
            "import sys, pathlib\n"
            f"pathlib.Path({str(folder / 'args')!r}).write_text(' '.join(sys.argv[1:]), encoding='utf-8')\n"
            f"pathlib.Path({str(folder / 'sent.pdf')!r}).write_bytes(sys.stdin.buffer.read())\n"
            f"sys.stderr.write('lp: printer is not ready')\nsys.exit({lp_code})\n",
        )
    monkeypatch.setenv("PATH", str(bin_folder))
    return folder


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
def test_既定のプリンターにlpで紙面を送りその名前を返す(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: 既定のプリンターが「経理室プリンター」の印刷システム。
    folder = system(tmp_path, monkeypatch, "経理室プリンター", 0)
    [document] = documents(1)
    # When
    name = printing.send(document)
    # Then
    assert name == "経理室プリンター"
    assert (folder / "args").read_text(encoding="utf-8") == "-d 経理室プリンター -t 請求書 -"
    assert (folder / "sent.pdf").read_bytes() == document.pdf


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
def test_lpstatが既定のプリンターを示さなければlpに送らずに断る(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: 既定のプリンターのない印刷システム。
    folder = system(tmp_path, monkeypatch, None, 0)
    # When
    with pytest.raises(printing.PrintRefused) as refused:
        printing.send(documents(1)[0])
    # Then
    assert refused.value.fix == printing.PrintFix("no_default_printer", "no system default destination")
    assert not (folder / "sent.pdf").exists()


@supports("test_既定のプリンターがないと整え方を示し整えて打ち直すと同じ番号で出る")
def test_lpstatがなければ既定のプリンターがないと断る(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: 印刷システムのコマンドのないノートPC。
    monkeypatch.setenv("PATH", str(tmp_path))
    # When
    with pytest.raises(printing.PrintRefused) as refused:
        printing.send(documents(1)[0])
    # Then
    assert refused.value.fix.problem == "no_default_printer"
    assert "lpstat" in refused.value.fix.detail


@supports("test_送る途中で送れなくなると整え方を示して止まる")
def test_lpが断れば印刷システムのわけとともに送れないと断る(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: 既定のプリンターはあるが、lp が断る印刷システム。
    system(tmp_path, monkeypatch, "経理室プリンター", 1)
    # When
    with pytest.raises(printing.PrintRefused) as refused:
        printing.send(documents(1)[0])
    # Then
    assert refused.value.fix == printing.PrintFix("send_failed", "lp: printer is not ready")


@supports("test_送る途中で送れなくなると整え方を示して止まる")
def test_lpがなければ送れないと断る(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: lpstat はあるが、lp のないノートPC。
    system(tmp_path, monkeypatch, "経理室プリンター", None)
    # When
    with pytest.raises(printing.PrintRefused) as refused:
        printing.send(documents(1)[0])
    # Then
    assert refused.value.fix.problem == "send_failed"
    assert "lp" in refused.value.fix.detail
