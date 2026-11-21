"""S2: 自分たちだけで使い始める道筋の結合ケース。"""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from invoice import command

supports = pytest.mark.supports

PRODUCT = Path(__file__).resolve().parents[2]
"""invoice の一式のフォルダー。"""


def uv(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """ガイドのインストーラーの uv を、ケースだけの置き場で動かす。"""
    env = os.environ | {
        "UV_TOOL_DIR": str(tmp_path / "tools"),
        "UV_TOOL_BIN_DIR": str(tmp_path / "bin"),
        "UV_CACHE_DIR": str(tmp_path / "cache"),
    }
    return subprocess.run(["uv", *args], capture_output=True, text=True, env=env, check=False)


@supports("S2")
def test_版を尋ねると版が示される(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # Given: invoice を入れたあと。
    monkeypatch.setattr(sys, "argv", ["invoice", "--version"])
    # When: 利用者が版を尋ねる。
    code = command.main()
    # Then: ガイドのとおりの版を示す。
    assert code == 0
    assert capsys.readouterr() == ("invoice 0.1.0\n", "")


@supports("S2", "P1.1")
def test_配布物を入れると版が示され書体もともに入る(tmp_path: Path) -> None:
    # Given: invoice の一式から作った配布物。
    built = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path / "dist"), str(PRODUCT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert built.returncode == 0, built.stderr
    [wheel] = (tmp_path / "dist").glob("invoice-0.1.0-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        fonts = [name for name in archive.namelist() if name.startswith("invoice/fonts/")]
    # When: 利用者が配布物を入れ、版を尋ねる。
    installed = uv(tmp_path, "tool", "install", str(wheel))
    version = subprocess.run(
        [str(tmp_path / "bin" / "invoice"), "--version"], capture_output=True, text=True, check=False
    )
    # Then: 書体をともに入れ終え、ガイドのとおりの版を示す。
    assert fonts != []
    assert installed.returncode == 0, installed.stderr
    assert (version.returncode, version.stdout) == (0, "invoice 0.1.0\n")
