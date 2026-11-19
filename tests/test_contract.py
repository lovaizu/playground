"""The contract cases: the real CUPS lp against the stand-in of tests/bin, for each recorded step.

They run only on a laptop with CUPS, where INVOICER_CUPS_STATE names the state that its printing
is in: takes, no-default, or refuses, as the stand-in's LP_STANDIN_STATE does. With takes, a page
prints. Each docstring names, after Supports, the elements of docs/architecture.md it shows.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import unittest

from harness import BIN

STATE = os.environ.get("INVOICER_CUPS_STATE", "")
TEXT = "invoicer contract test\n"


def lp(command: str, env: dict) -> subprocess.CompletedProcess:
    """`command` run as lp is, the text on its input and no printer named."""
    return subprocess.run(
        [command], input=TEXT, env=env, capture_output=True, text=True, check=False
    )


@unittest.skipUnless(
    STATE in ("takes", "no-default", "refuses"),
    "set INVOICER_CUPS_STATE on a laptop with CUPS",
)
class ContractTest(unittest.TestCase):
    """The stand-in answers as the real lp does, in the state that INVOICER_CUPS_STATE names."""

    def test_the_stand_in_answers_as_cups_does(self) -> None:
        """Supports: printer, P5.3.

        Given CUPS in the state that INVOICER_CUPS_STATE names, and the stand-in set to it.
        When each runs with the same text and no printer named.
        Then both end with the same status, and the stand-in's words begin as CUPS's do.
        """
        real = shutil.which("lp", path=os.environ.get("PATH", "").replace(str(BIN), ""))
        self.assertIsNotNone(real, "CUPS's lp isn't on the path")
        assert real is not None
        cups = lp(real, dict(os.environ))
        stand_in = lp(
            str(BIN / "lp"),
            dict(os.environ, LP_STANDIN_STATE=STATE, LP_STANDIN_LOG=os.devnull),
        )
        self.assertEqual(stand_in.returncode == 0, cups.returncode == 0, cups.stderr)
        if STATE == "takes":
            self.assertTrue(cups.stdout.startswith("request id is"), cups.stdout)
        elif STATE == "no-default":
            self.assertIn("no default destination", cups.stderr.lower())
        else:
            self.assertTrue(cups.stderr.startswith("lp: "), cups.stderr)
            self.assertIn("not accepting jobs", cups.stderr)


if __name__ == "__main__":
    unittest.main()
