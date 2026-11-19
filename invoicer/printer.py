"""How an invoice reaches the default printer through CUPS, and what each failure asks to check."""

from __future__ import annotations

import subprocess

from invoicer.invoice import Invoice


def lp(text: str) -> subprocess.CompletedProcess[str]:
    """CUPS's lp, run with the text on its input and no printer named.

    Takes: the text to print.
    Gives: lp's exit status and what it wrote, as subprocess gives them.
    Changes: hands a job to the default printer where lp takes it.
    Refuses: FileNotFoundError where no lp is on the path.
    """
    raise NotImplementedError("printer.lp")


def send(invoice: Invoice) -> None:
    """The invoice handed to the default printer, by lp.

    Takes: the invoice that the command has shown.
    Gives: nothing, once lp has taken the job.
    Changes: the default printer prints the invoice's text.
    Refuses: Refusal with `check` set to the Requirement to check: where lp is missing, naming
    cups-client to install; where no default printer is set, naming `lpstat -d`; and where CUPS
    refuses the job, with CUPS's own reason.
    """
    raise NotImplementedError("printer.send")
