"""印刷 (printing.print_documents, printing.send) の単体ケース。"""

from __future__ import annotations

import pytest

from invoice import layout, printing
from invoice.layout import PrintDocument
from invoice.printing import Printed
from tests.given import README_INVOICE, Printer

supports = pytest.mark.supports


def documents(*sheets: int) -> list[PrintDocument]:
    return [PrintDocument(pdf=b"%PDF-" + bytes([i]), sheets=count) for i, count in enumerate(sheets)]


@supports("test_明細から請求書が印刷され番号と金額と枚数が示される")
@pytest.mark.parametrize("sheets", [(1,), (2,), (1, 3, 1)])
def test_紙面を受け取った順に送り既定のプリンターの名前と送った用紙の枚数を返す(
    printer: Printer, sheets: tuple[int, ...]
) -> None:
    # Given: 一枚か二枚の紙面が一つ、またはいくつかの紙面。明細には一行以上あるので、紙面は一つ以上ある。
    #   既定のプリンターの名前は、ガイドの例と違う「2階の複合機」。
    printer.name = "2階の複合機"
    given = documents(*sheets)
    # When
    sent = printing.print_documents(given)
    # Then
    assert sent == Printed(printer="2階の複合機", sheets=sum(sheets))
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
    name = printing.send(document)
    # Then: 印刷システムが断らずに受け付け、PrintRefused が上がらず、既定のプリンターの名前を返す。
    assert name != ""
