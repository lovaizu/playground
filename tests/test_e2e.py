"""The end-to-end cases: invoicer installed fresh from the checked-out branch, as the README says.

Each case installs by the README's command, pipx install, pointed at this checkout, into a home
of its own, then runs as one from accounting or one who builds invoices in Python does. The
stand-in lp of tests/bin comes first on the path, so no paper prints. Each docstring names, after
Supports, the key result of docs/product-vision.md that it supports.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

import spreadsheet
from harness import BIN, ROOT
from spreadsheet import SENT, WALKTHROUGH_ARGS, WALKTHROUGH_INVOICE, WALKTHROUGH_ROWS

# What one who builds invoices in Python writes: the walkthrough's lines, at 19%, through the
# library's public calls alone.
LIBRARY_USE = """
from decimal import Decimal
import invoicer
lines = invoicer.parse_lines("Bookkeeping, October;85.00;12\\nPayroll, October;14.50;9\\nAnnual accounts 2025;450.00;1")
rate = Decimal("0.19")
amount = invoicer.subtotal(lines)
print(amount, invoicer.tax_of(amount, rate), invoicer.total(lines, rate))
print(invoicer.render(lines, rate))
"""


# What the copy of the checkout leaves out: the repository's history and what a build or a run
# leaves behind.
LEFT_OUT = (
    ".git",
    ".rn",
    "build",
    "*.egg-info",
    "__pycache__",
    ".ruff_cache",
    ".mypy_cache",
)


class Installed:
    """invoicer installed by pipx into a home of its own, and a folder to run it in."""

    def __init__(self) -> None:
        """Installs the checked-out branch fresh, as the README's install command does."""
        if shutil.which("pipx") is None:
            raise AssertionError(
                "pipx isn't on the path: install it as the README's Requirements say"
            )
        self._home = tempfile.TemporaryDirectory()
        home = Path(self._home.name)
        self.folder = home / "work"
        self.folder.mkdir()
        self.log = home / "lp.jsonl"
        self.python = home / "pipx" / "venvs" / "invoicer" / "bin" / "python"
        self.env = dict(
            os.environ,
            PIPX_HOME=str(home / "pipx"),
            PIPX_BIN_DIR=str(home / "bin"),
            PIPX_MAN_DIR=str(home / "man"),
        )
        # A copy of the checkout, so that the build leaves nothing in the checkout itself.
        branch = home / "branch"
        shutil.copytree(ROOT, branch, ignore=shutil.ignore_patterns(*LEFT_OUT))
        done = subprocess.run(
            ["pipx", "install", str(branch)],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode != 0:
            raise AssertionError(f"pipx install failed:\n{done.stdout}{done.stderr}")
        self.env.update(
            PATH=os.pathsep.join(
                [str(BIN), str(home / "bin"), os.environ.get("PATH", "")]
            ),
            LP_STANDIN_LOG=str(self.log),
            LP_STANDIN_STATE="takes",
        )

    def run(self, argv: list[str]) -> subprocess.CompletedProcess:
        """One run of the installed `invoicer` in the folder, as typed in the terminal."""
        return subprocess.run(
            ["invoicer", *argv],
            cwd=self.folder,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def jobs(self) -> list[dict[str, object]]:
        """What lp got, one entry for each run of it."""
        if not self.log.exists():
            return []
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
        ]

    def cleanup(self) -> None:
        """Removes the home and all that the install put in it."""
        self._home.cleanup()


class AccountingTest(unittest.TestCase):
    """O1: one from accounting prints the invoice, with no developer."""

    def test_kr1_1_the_walkthroughs_invoice_prints_right(self) -> None:
        """Supports: KR1.1.

        Given invoicer installed fresh, and the walkthrough's October.ods in the folder.
        When one from accounting runs the walkthrough's command line, at --rate 19.
        Then the terminal shows `Tax rate: 19%`, a subtotal of 1600.50 EUR, a tax of 304.10 EUR,
        and a total of 1904.60 EUR in the walkthrough's invoice dated today, then that it went
        to the default printer; lp gets the same invoice; and the run ends with 0.
        """
        installed = Installed()
        self.addCleanup(installed.cleanup)
        spreadsheet.write(str(installed.folder / "October.ods"), WALKTHROUGH_ROWS)
        done = installed.run(WALKTHROUGH_ARGS)
        invoice = WALKTHROUGH_INVOICE.format(today=date.today().isoformat())
        for shown in ("Tax rate: 19%", "1600.50 EUR", "304.10 EUR", "1904.60 EUR"):
            self.assertIn(shown, done.stdout, done.stderr)
        self.assertEqual(done.stdout.rstrip("\n"), f"{invoice}\n\n{SENT}")
        jobs = installed.jobs()
        self.assertEqual([str(job["input"]).rstrip("\n") for job in jobs], [invoice])
        self.assertEqual(done.returncode, 0)

    def test_kr1_2_the_sample_prints_right_after_the_install(self) -> None:
        """Supports: KR1.2.

        Given invoicer just installed fresh, and nothing else set up.
        When one from accounting runs `invoicer --sample`.
        Then the terminal shows the sample invoice of 119.00 EUR, then that it went to the
        default printer; lp gets the same invoice; and the run ends with 0.
        """
        installed = Installed()
        self.addCleanup(installed.cleanup)
        done = installed.run(["--sample"])
        self.assertRegex(done.stdout, r"(?m)^Total +119\.00 EUR$")
        self.assertTrue(
            done.stdout.rstrip("\n").endswith(f"\n\n{SENT}"), done.stdout + done.stderr
        )
        invoice = done.stdout.rstrip("\n")[: -len(SENT)].rstrip("\n")
        self.assertEqual(
            [str(job["input"]).rstrip("\n") for job in installed.jobs()], [invoice]
        )
        self.assertEqual(done.returncode, 0)


class PythonTest(unittest.TestCase):
    """O2: one who builds invoices in Python gets the sums and text in their code."""

    def setUp(self) -> None:
        """Installs invoicer fresh."""
        self.installed = Installed()
        self.addCleanup(self.installed.cleanup)

    def library(self) -> subprocess.CompletedProcess:
        """LIBRARY_USE, run by the Python that invoicer is installed in."""
        return subprocess.run(
            [str(self.installed.python), "-I", "-c", LIBRARY_USE],
            cwd=self.installed.folder,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_kr2_1_the_sums_and_text_come_out_right(self) -> None:
        """Supports: KR2.1.

        Given invoicer installed fresh, and the walkthrough's lines and rate in their code.
        When the code hands them to the library.
        Then it gets 1600.50, 304.10, and 1904.60, and the walkthrough's rows and sums.
        """
        done = self.library()
        self.assertEqual(
            done.stdout.splitlines()[0], "1600.50 304.10 1904.60", done.stderr
        )
        rows = WALKTHROUGH_INVOICE.split("\n\n", 1)[1]
        self.assertEqual(done.stdout.split("\n", 1)[1].rstrip("\n"), rows)

    def test_kr2_2_the_public_calls_alone_give_the_invoice(self) -> None:
        """Supports: KR2.2.

        Given invoicer installed fresh.
        When code imports the package and asks for help on each of its public calls.
        Then each is there and says what it gives, and the library's use runs with them alone.
        """
        check = "import invoicer\nfor name in invoicer.__all__:\n    assert getattr(invoicer, name).__doc__, name\n"
        done = subprocess.run(
            [str(self.installed.python), "-I", "-c", check],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.library().returncode, 0)


if __name__ == "__main__":
    unittest.main()
