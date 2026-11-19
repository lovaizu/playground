"""How a page reaches the laptop's default printer: an adapter to Linux's `lp` printing command."""

import subprocess

_SET_A_PRINTER = "set a default printer in Settings, then Printers, and check that `lpstat -d` shows it"


class PrintError(Exception):
    """No printer took the page; its message gives `lp`'s own reason and what to set up."""


def print_page(text: str) -> None:
    """Hands text, the whole page, to `lp` for the default printer, naming no printer, and `lp`
    breaks a long page across sheets of paper. It gives once `lp` exits 0.

    Refuses: PrintError, where `lp` isn't on PATH, saying so and to set a default printer; and
    where `lp` exits nonzero, with `lp`'s own reason, such as `lp: The printer or class does not
    exist.`, followed by the hint to set a default printer where `lp` names no default printer
    or gives no reason."""
    try:
        lp_result = subprocess.run(
            ["lp"], input=text, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError:
        raise PrintError(f"the printing command `lp` isn't on this laptop: {_SET_A_PRINTER}") from None
    if lp_result.returncode != 0:
        reason = lp_result.stderr.strip()
        if not reason:
            raise PrintError(f"no printer took the invoice: {_SET_A_PRINTER}")
        if "no default destination" in reason.lower():
            # The reason's full stop comes off, so the hint follows it after a colon, not `.:`.
            raise PrintError(f"{reason.rstrip('.')}: {_SET_A_PRINTER}")
        raise PrintError(reason)
