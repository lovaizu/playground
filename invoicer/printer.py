"""How an invoice reaches the default printer through CUPS, and what each failure asks to check."""

from __future__ import annotations

import subprocess

from invoicer.invoice import Invoice
from invoicer.refusal import Refusal

_CUPS_CLIENT = (
    "cups-client, from sudo apt install cups-client or sudo dnf install cups-client"
)
_DEFAULT_PRINTER = "lpstat -d shows system default destination: and its name"


def lp(text: str) -> subprocess.CompletedProcess[str]:
    """CUPS's lp, run with the text on its input and no printer named.

    Takes: the text to print.
    Gives: lp's exit status and what it wrote, as subprocess gives them.
    Changes: hands a job to the default printer where lp takes it.
    Refuses: FileNotFoundError where no lp is on the path.
    """
    return subprocess.run(
        ["lp"], input=text, capture_output=True, encoding="utf-8", check=False
    )


def send(invoice: Invoice) -> None:
    """The invoice handed to the default printer, by lp.

    Takes: the invoice that the command has shown.
    Gives: nothing, once lp has taken the job.
    Changes: the default printer prints the invoice's text.
    Refuses: Refusal with `check` set to the Requirement to check: where lp is missing, naming
    cups-client to install; where no default printer is set, naming `lpstat -d`; and where CUPS
    refuses the job, with CUPS's own reason.
    """
    try:
        done = lp(invoice.text)
    except FileNotFoundError:
        raise Refusal(
            "lp, the print command of CUPS, isn't on this laptop, so the invoice didn't print.",
            check=_CUPS_CLIENT,
        ) from None
    if done.returncode == 0:
        return
    reason = done.stderr.strip()
    if "no default destination" in reason.lower():
        raise Refusal(
            f"no default printer is set, so the invoice didn't print. CUPS says: {reason}",
            check=_DEFAULT_PRINTER,
        )
    raise Refusal(
        f"the printer didn't take the invoice, so it didn't print. CUPS says: {reason}",
        check=_DEFAULT_PRINTER,
    )
