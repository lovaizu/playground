"""発行者情報の形を、尋ねる事柄とその順と名前から、残すファイルの中身まで決める。"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal, TypeAlias, cast

from invoice import place
from invoice.width import narrowed

IssuerItem: TypeAlias = Literal[
    "name",
    "registration_number",
    "payment_terms",
    "bank_name",
    "bank_branch",
    "account_type",
    "account_number",
    "account_holder",
]
"""発行者情報の事柄。名称、登録番号、支払条件 (P3.1, P3.9) と、
お振込先の銀行名、支店名、口座種別、口座番号、口座名義。"""

Day: TypeAlias = int | Literal["month_end"]
"""締め日か支払日。1 から 28 の日か、月末 (P3.12)。"""


@dataclass(frozen=True)
class PaymentTerms:
    """支払条件を、締め日、支払の月、支払日の三つの値で表す。"""

    closing_day: Day
    """締め日。"""
    month: Literal[0, 1, 2]
    """支払の月。0 は当月、1 は翌月、2 は翌々月。"""
    payment_day: Day
    """支払日。"""


Answer: TypeAlias = str | PaymentTerms
"""確かめ終えた一つの答え。支払条件は PaymentTerms、ほかの事柄は str。"""


@dataclass(frozen=True)
class BankAccount:
    """お振込先: 取引先が請求額を振り込む、発行者の口座。"""

    name: str
    """銀行名。例: `さくら銀行`。"""
    branch: str
    """支店名。例: `本店営業部`。"""
    account_type: Literal["普通", "当座"]
    """口座種別。"""
    account_number: str
    """口座番号。7 桁の数字。"""
    account_holder: str
    """口座名義。カナ。例: `カ)アオバジムヨウヒン`。"""


@dataclass(frozen=True)
class Issuer:
    """発行者情報: 請求書を出す側として毎回載せる事柄と、支払条件。"""

    name: str
    """発行者の名称。"""
    registration_number: str
    """適格請求書発行事業者の登録番号。T と 13 桁の数字。"""
    payment_terms: PaymentTerms
    """支払条件。"""
    bank: BankAccount
    """お振込先。請求書にそのまま載せる。"""


@dataclass(frozen=True)
class Question:
    """尋ねる一つの事柄。コマンドはこの値だけから問いを示す。

    尋ねる事柄、その順、利用者に見せる名前と例を決めるのは、このモジュールだけ。
    """

    item: IssuerItem
    """事柄。"""
    label: str
    """利用者に見せる事柄の名前。例: `登録番号(T と 13 桁の数字)`。"""
    example: str
    """受け付ける形の例。例: `T1234567890123`。"""


@dataclass(frozen=True)
class AnswerFix:
    """直すところ: 形に合わない一つの答えと、受け付ける形の例。"""

    item: IssuerItem
    """答えが形に合わなかった事柄。"""
    given: str
    """利用者の答え。"""
    expected: str
    """受け付ける形の例。そのまま答えれば受け付ける。例: `20日締め翌月10日払い`。"""
    rule: str
    """受け付ける形の決まりを、利用者の言葉で。事柄の名前は含まない。
    例: `締め日と支払日は、1日から28日か月末です。`。"""


class AnswerRefused(Exception):
    """答えが形に合わないときに上がり、直すところを持つ。"""

    def __init__(self, fix: AnswerFix) -> None:
        super().__init__(fix)
        self.fix = fix


class AnswersIncomplete(Exception):
    """残させた答えに欠けた事柄があるときに上がり、欠けた事柄を持つ。"""

    def __init__(self, missing: tuple[IssuerItem, ...]) -> None:
        super().__init__(missing)
        self.missing = missing


_FILE = "issuer.json"
"""置き場の中の、発行者情報のファイルの名前。"""

_QUESTIONS = (
    Question("name", "発行者の正式名称", "株式会社あおば事務用品"),
    Question("registration_number", "登録番号(T と 13 桁の数字)", "T1234567890123"),
    Question("payment_terms", "締め日と支払条件(例: 月末締め翌月末払い)", "月末締め翌月末払い"),
    Question("bank_name", "お振込先の銀行名", "さくら銀行"),
    Question("bank_branch", "支店名", "本店営業部"),
    Question("account_type", "口座種別(普通か当座)", "普通"),
    Question("account_number", "口座番号", "1234567"),
    Question("account_holder", "口座名義(カナ)", "カ)アオバジムヨウヒン"),
)
"""尋ねる事柄を、尋ねる順に (P2.1)。"""

_ITEMS: tuple[IssuerItem, ...] = tuple(question.item for question in _QUESTIONS)

_TERMS = re.compile(r"(?:(?P<closing>[0-9]+)日|月末)締め(?P<month>当月|翌月|翌々月)(?:(?P<payment>[0-9]+)日|末)払い")
"""「20日締め翌月10日払い」の形の支払条件 (P3.10)。"""

_MONTHS: dict[str, Literal[0, 1, 2]] = {"当月": 0, "翌月": 1, "翌々月": 2}

_HOLDER = re.compile(r"[ァ-ヴー0-9A-Z().,/\- ]+")
"""口座名義に使えるカナと、数字、英大文字、記号。"""


def load() -> Issuer | tuple[Question, ...]:
    """残した情報を求める (S1, S3)。

    受け取る: なし。置き場の場所は place.folder から受け取る。
    返す: 残した発行者情報。
        まだ残していなければ、尋ねる事柄を尋ねる順に (P2.1)。
        名称、登録番号、支払条件、銀行名、支店名、口座種別、口座番号、口座名義の順。
        尋ねる事柄の一覧とその順と名前を持つのは、このモジュールだけ。
    ほかに変えるもの: なし。
    断るとき:
        place.StoreRefused: 発行者情報のファイルが読めない、または壊れているとき。
            残したときの形に合わない中身も、壊れているとする。
    """
    stored = place.read(_FILE)
    if stored is None:
        return _QUESTIONS
    try:
        return _issuer({item: check(item, _stored_answer(stored, item)) for item in _ITEMS})
    except (AnswerRefused, KeyError, TypeError, ValueError) as error:
        raise place.broken(_FILE, f"発行者情報の形に合わない: {error!r}") from error


def check(item: IssuerItem, answer: str) -> Answer:
    """答えを確かめさせる (S3)。

    受け取る: 尋ねた事柄と、利用者の答えの文字列。
        全角の数字・英字・記号は半角に、半角カナは全角に読み替えてから確かめる。
    返す: 確かめ終えた答え。読み替えたあとの文字列。支払条件は三つの値に読み取る (P3.10)。
    ほかに変えるもの: なし。何も残さない (P2.4)。
    断るとき:
        AnswerRefused: 答えが事柄の形に合わないとき。支払条件では、
            「20日締め翌月10日払い」の形でないとき (P3.10)、
            締め日か支払日が 1 から 28 の日でも月末でもないとき (P3.12)、
            当月払いで支払日が締め日より後でないとき (P3.11)。
            登録番号では、T と 13 桁の数字でないとき。
            お振込先では、口座種別が「普通」でも「当座」でもないとき、
            口座番号が 7 桁の数字でないとき、口座名義がカナでないとき。
            どの事柄でも、答えが空のとき。
    """
    text = narrowed(answer)
    if text == "":
        raise AnswerRefused(AnswerFix(item, answer, _example(item), "答えが空です。"))
    return _CHECKS[item](item, answer, text)


def save(answers: Mapping[IssuerItem, Answer]) -> Issuer:
    """すべての答えを残させる (S3)。

    受け取る: check が返した答えを、事柄ごとに。
    返す: 残した発行者情報。
    ほかに変えるもの: 発行者情報を、place.folder の中に、すべて一度に残す (P2.4)。
    断るとき:
        AnswersIncomplete: 欠けた事柄があるとき。欠けた事柄を、尋ねる順に持つ。何も残さない (P2.4)。
        place.StoreRefused: 発行者情報のファイルを書けないとき。何も残さない (P2.4)。
    """
    missing = tuple(item for item in _ITEMS if item not in answers)
    if missing:
        raise AnswersIncomplete(missing)
    issuer = _issuer(answers)
    place.write(_FILE, asdict(issuer))
    return issuer


def _example(item: IssuerItem) -> str:
    return next(question.example for question in _QUESTIONS if question.item == item)


def _refused(item: IssuerItem, answer: str, rule: str, expected: str | None = None) -> AnswerRefused:
    return AnswerRefused(AnswerFix(item, answer, expected or _example(item), rule))


def _text(item: IssuerItem, answer: str, text: str) -> Answer:
    return text


def _registration_number(item: IssuerItem, answer: str, text: str) -> Answer:
    if re.fullmatch(r"T[0-9]{13}", text) is None:
        raise _refused(item, answer, "T のあとに 13 桁の数字を続けて答えてください。")
    return text


def _account_type(item: IssuerItem, answer: str, text: str) -> Answer:
    if text not in ("普通", "当座"):
        raise _refused(item, answer, "「普通」か「当座」のどちらかで答えてください。")
    return text


def _account_number(item: IssuerItem, answer: str, text: str) -> Answer:
    if re.fullmatch(r"[0-9]{7}", text) is None:
        raise _refused(item, answer, "7 桁の数字で答えてください。")
    return text


def _account_holder(item: IssuerItem, answer: str, text: str) -> Answer:
    if _HOLDER.fullmatch(text) is None:
        raise _refused(item, answer, "通帳にあるとおりのカタカナで答えてください。")
    return text


def _payment_terms(item: IssuerItem, answer: str, text: str) -> Answer:
    found = _TERMS.fullmatch(text)
    if found is None:
        raise _refused(
            item,
            answer,
            "締め日、当月か翌月か翌々月、支払日を、この順に並べて答えてください。",
            "20日締め翌月10日払い",
        )
    closing, payment = _day(found["closing"]), _day(found["payment"])
    if closing is None or payment is None:
        raise _refused(item, answer, "締め日と支払日は、1日から28日か月末です。", "20日締め翌月10日払い")
    terms = PaymentTerms(closing, _MONTHS[found["month"]], payment)
    if terms.month == 0 and not _after(terms.payment_day, terms.closing_day):
        raise _refused(item, answer, "当月払いでは、支払日を締め日より後の日にしてください。", "10日締め当月25日払い")
    return terms


def _day(digits: str | None) -> Day | None:
    """「20日」の 20 か、月末を表す None の数字から、締め日か支払日。範囲の外なら None。"""
    if digits is None:
        return "month_end"
    day = int(digits)
    return day if 1 <= day <= 28 else None


def _after(payment: Day, closing: Day) -> bool:
    """支払日が、同じ月の締め日より後か。"""
    if closing == "month_end":
        return False
    return payment == "month_end" or payment > closing


_CHECKS: dict[IssuerItem, Callable[[IssuerItem, str, str], Answer]] = {
    "name": _text,
    "registration_number": _registration_number,
    "payment_terms": _payment_terms,
    "bank_name": _text,
    "bank_branch": _text,
    "account_type": _account_type,
    "account_number": _account_number,
    "account_holder": _account_holder,
}


def _issuer(answers: Mapping[IssuerItem, Answer]) -> Issuer:
    """check が確かめ終えた答えから、発行者情報。"""

    def text(item: IssuerItem) -> str:
        return cast(str, answers[item])

    return Issuer(
        name=text("name"),
        registration_number=text("registration_number"),
        payment_terms=cast(PaymentTerms, answers["payment_terms"]),
        bank=BankAccount(
            name=text("bank_name"),
            branch=text("bank_branch"),
            account_type=cast(Literal["普通", "当座"], text("account_type")),
            account_number=text("account_number"),
            account_holder=text("account_holder"),
        ),
    )


def _stored_answer(stored: Any, item: IssuerItem) -> Any:
    """残したファイルの中身から、事柄の答えを、利用者が答える形で。"""
    bank = stored["bank"]
    fields: dict[IssuerItem, Callable[[], Any]] = {
        "name": lambda: stored["name"],
        "registration_number": lambda: stored["registration_number"],
        "payment_terms": lambda: _said(stored["payment_terms"]),
        "bank_name": lambda: bank["name"],
        "bank_branch": lambda: bank["branch"],
        "account_type": lambda: bank["account_type"],
        "account_number": lambda: bank["account_number"],
        "account_holder": lambda: bank["account_holder"],
    }
    return fields[item]()


def _said(terms: Any) -> str:
    """残した三つの値の支払条件を、「20日締め翌月10日払い」の形で。"""
    names = {value: name for name, value in _MONTHS.items()}
    closing = "月末" if terms["closing_day"] == "month_end" else f"{_whole(terms['closing_day'])}日"
    payment = "末" if terms["payment_day"] == "month_end" else f"{_whole(terms['payment_day'])}日"
    return f"{closing}締め{names[terms['month']]}{payment}払い"


def _whole(value: Any) -> int:
    """残した日の値。整数でなければ ValueError。"""
    if type(value) is not int:
        raise ValueError(value)
    return value
