"""部品の結果と直すところを、利用者に端末でどう示すか。"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from importlib import metadata
from pathlib import Path

from invoice import billing, issuer, layout, ledger, place, printing

_USAGE = "使い方: invoice <明細のファイル.csv>\n       invoice --version\n"

_ISSUES = "https://github.com/lovaizu/playground/issues"


class _Stopped(Exception):
    """尋ねる途中で、利用者が答えずに止めた。"""


def main(argv: Sequence[str] | None = None) -> int:
    """明細のファイルを渡す (S1, S3, S4)、版を尋ねる (S2)。

    受け取る: コマンドラインの引数。明細のファイルのパス一つか、`--version`。
        None のときは sys.argv[1:] を使う。
    返す: 終了コード。
        0: 印刷を頼み終え、請求書ごとの宛名と番号と金額と、既定のプリンターの名前と
           印刷した枚数を示した (P2.6)。`--version` では版を示した (S2)。
        1: 直すところを示して止まった (P1.2)。
        2: 引数が明細のファイル一つでも `--version` でもなく、使い方を示した。
        130: 発行者情報を尋ねる途中で、利用者が Ctrl+C で答えずに止めた (P2.4)。
    ほかに変えるもの:
        端末で尋ね、示す。利用者と言葉を交わすのは、このモジュールだけ (P1.2)。
        明細に直すところがないときにだけ、発行者情報を求め、印刷に進む (P2.5)。
        発行者情報がないときは、issuer.load が返した事柄を、受け取った順に、
        その名前のとおりに尋ねるだけ。何をどの順に尋ねるかは決めない。
        初回は、すべての答えがそろったときにだけ発行者情報を残させる (P2.4)。
        番号の採番を通して発行記録を、印刷を通して既定のプリンターを動かす。
    断るとき:
        ledger.LedgerRefused: すべての直すところを、その problem ごとに示し、
            何も尋ねず、何も印刷せずに 1 を返す (P1.3, P2.5)。
            not_found: そのパスにファイルがないことと、パスの確かめ方を示す。
            unreadable: そのファイルを読めないことと、UTF-8 の CSV での保存し直し方を示す。
            no_rows: 明細に行が一つもないことと、一行の例を示す。
            bad_value: 行と列と書かれていた値と、受け付ける形の決まりと例を示す。
        issuer.AnswerRefused: 受け付ける形の決まりと例を示し、同じ事柄を尋ね直す (P1.5)。
        place.StoreRefused: どのファイルの何が問題かと直し方を示し、
            何も印刷せずに 1 を返す。
        printing.PrintRefused: プリンターの整え方を示して 1 を返す (S4)。
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--version"]:
        print(f"invoice {metadata.version('invoice')}")
        return 0
    if len(args) != 1:
        sys.stderr.write(_USAGE)
        return 2
    try:
        return _print(Path(args[0]))
    except ledger.LedgerRefused as refused:
        _show_ledger(refused.fixes)
    except place.StoreRefused as refused:
        _show_store(refused.fix)
    except printing.PrintRefused as refused:
        _show_printer(refused.fix)
    except _Stopped:
        print("\ninvoice: 止めました。発行者の情報は何も残していません。次に打ったときに、初めから伺います。")
        return 130
    return 1


def _print(path: Path) -> int:
    """明細から請求書を印刷し、請求書ごとの番号と金額と、印刷した枚数を示す (S1)。"""
    rows = ledger.read(path)
    found = issuer.load()
    issuer_info = found if isinstance(found, issuer.Issuer) else _ask(found)
    invoices = billing.bill(rows, issuer_info)
    printed = printing.print_documents(layout.typeset(invoices))
    for invoice in invoices:
        print(
            f"{invoice.customer.name} {invoice.customer.honorific}: "
            f"請求書番号 {invoice.number}、ご請求金額 {invoice.amount:,} 円"
        )
    print(f"既定のプリンター「{printed.printer}」で {printed.sheets} 枚を印刷しました。")
    return 0


def _ask(questions: tuple[issuer.Question, ...]) -> issuer.Issuer:
    """事柄を順に尋ね、すべての答えがそろってから発行者情報として残させる (S3)。"""
    print("はじめて使うので、発行者の情報を伺います。次からは聞きません。")
    answers: dict[issuer.IssuerItem, issuer.Answer] = {}
    for question in questions:
        while question.item not in answers:
            try:
                answers[question.item] = issuer.check(question.item, _answer(question.label))
            except issuer.AnswerRefused as refused:
                fix = refused.fix
                said = f"「{fix.given}」は受け付けられません。" if fix.given else ""
                print(f"{said}{fix.rule}たとえば「{fix.expected}」のように答えてください。")
    # 端末でない入力では答えが画面に出ず、最後の問いの行が閉じないので、ここで行を改める。
    print()
    return issuer.save(answers)


def _answer(label: str) -> str:
    """一つの事柄を尋ね、利用者が打った一行を、改行を除いて。"""
    sys.stdout.write(f"{label}: ")
    sys.stdout.flush()
    try:
        line = sys.stdin.readline()
    except KeyboardInterrupt as error:
        raise _Stopped from error
    return line.rstrip("\r\n")


def _show_ledger(fixes: tuple[ledger.LedgerFix, ...]) -> None:
    print("invoice: 明細を請求書にできませんでした。次のところを直して保存し、同じコマンドを打ち直してください。")
    print("何も印刷していません。")
    for fix in fixes:
        if fix.problem == "not_found":
            print(
                f"- {fix.path}: このファイルが見つかりません。"
                "ファイルの名前と、端末を開いたフォルダーを確かめてください。"
                "明細を保存したフォルダーで「端末で開く」を選ぶと、ファイルの名前だけで渡せます。"
            )
        elif fix.problem == "unreadable":
            print(
                f"- {fix.path}: このファイルを、UTF-8 の CSV として読めません ({fix.detail})。"
                "表計算ソフトで明細を開き、「ファイル」→「名前を付けて保存」で、"
                "種類を「テキスト CSV (.csv)」、文字セットを「Unicode (UTF-8)」にして保存し直してください。"
            )
        elif fix.problem == "no_rows":
            print(
                f"- {fix.path}: 見出しの行のほかに、明細の行がありません。"
                "見出しの下に、たとえば次の行を書き足してください。"
            )
            print(f"  {fix.expected}")
        else:
            given = f"「{fix.given}」は受け付けられません" if fix.given is not None else "値がありません"
            print(
                f"- {fix.path} の {fix.line} 行目、「{fix.column}」の列: {given}。"
                f"{fix.rule}たとえば「{fix.expected}」と書きます。"
            )


def _show_store(fix: place.StoreFix) -> None:
    print(f"invoice: 発行者の情報と請求書番号を残すファイル {fix.path} で止まりました。何も印刷していません。")
    if fix.problem == "unreadable":
        print(
            f"このファイルを読む権限がありません ({fix.detail})。"
            "端末で次を打ってから、同じコマンドを打ち直してください。"
        )
        print(f"  chmod u+rw '{fix.path}'")
    elif fix.problem == "broken":
        print(
            "このファイルの中身が壊れていて、読めません。"
            "バックアップがあれば戻してから、同じコマンドを打ち直してください。"
            f"戻せないときは、この画面の文を貼って {_ISSUES} で尋ねてください。"
        )
    else:
        print(
            f"このファイルを書けません ({fix.detail})。ホームフォルダーの空きと権限を確かめ、"
            "端末で次を打ってから、同じコマンドを打ち直してください。"
        )
        print(f"  mkdir -p '{fix.path.parent}' && chmod u+rwx '{fix.path.parent}'")


def _show_printer(fix: printing.PrintFix) -> None:
    if fix.problem == "no_default_printer":
        print(
            "invoice: 既定のプリンターが見つからないため、印刷できませんでした。"
            "「設定」の「プリンター」でプリンターを足して既定にし、端末で lpstat -d を打って"
            "名前が出ることを確かめてから、同じコマンドを打ち直してください。請求書番号は変わりません。"
        )
    else:
        print(
            f"invoice: 既定のプリンターに送れませんでした ({fix.detail})。"
            "プリンターの電源と用紙と接続を確かめてから、同じコマンドを打ち直してください。"
            "すでに出た請求書も、同じ番号でもう一度印刷されます。"
        )
