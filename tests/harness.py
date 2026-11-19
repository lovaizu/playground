"""The ground that the integration cases run the command on, as on an accounting laptop.

Each case runs in a folder of its own, where it builds its .ods file, with the stand-in lp of
tests/bin first on the path, and reads what the terminal showed and what lp got.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from unittest import mock

BIN = Path(__file__).resolve().parent / "bin"
ROOT = BIN.parent.parent


class Folder(unittest.TestCase):
    """A case run in a folder of its own, with the stand-in lp first on the path."""

    def setUp(self) -> None:
        """Makes the folder, moves into it, and puts the stand-in lp first on the path."""
        held = tempfile.TemporaryDirectory()
        self.addCleanup(held.cleanup)
        self.folder = Path(held.name)
        before = os.getcwd()
        os.chdir(self.folder)
        self.addCleanup(os.chdir, before)
        self.log = self.folder / "lp.jsonl"
        environ = mock.patch.dict(
            os.environ,
            {
                "PATH": f"{BIN}{os.pathsep}{os.environ.get('PATH', '')}",
                "LP_STANDIN_LOG": str(self.log),
                "LP_STANDIN_STATE": "takes",
            },
        )
        environ.start()
        self.addCleanup(environ.stop)

    def printer_answers(self, state: str) -> None:
        """Sets how the stand-in answers: takes, no-default, or refuses."""
        os.environ["LP_STANDIN_STATE"] = state

    def without_lp(self) -> None:
        """Leaves only an empty folder on the path, so no lp is found."""
        empty = self.folder / "empty-bin"
        empty.mkdir()
        os.environ["PATH"] = str(empty)

    def jobs(self) -> list[dict[str, Any]]:
        """What lp got, one entry for each run of it: its arguments and its input."""
        if not self.log.exists():
            return []
        with open(self.log, encoding="utf-8") as record:
            return [json.loads(line) for line in record]

    def invoicer(self, argv: Sequence[str]) -> tuple[int, str, str]:
        """The exit status, terminal output, and error output of one run of the command."""
        from invoicer import cli

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()
