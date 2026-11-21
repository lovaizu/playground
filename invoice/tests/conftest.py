"""invoice のケースが受け取る、まっさらなホームフォルダー、明細のファイル、端末とプリンターの代役。"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from invoice import printing
from invoice.issuer import Issuer
from tests.given import Printer, Terminal, save_aoba


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--host", action="store_true", help="本物の印刷システムを動かすケースも走らせる")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "supports(*names): ケースが確かめる、一つ上の段の要素かケース")
    config.addinivalue_line("markers", "host: 本物の印刷システムを動かすケース。--host のときだけ走る")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--host"):
        return
    for item in items:
        if "host" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="本物の印刷システムを動かすため、--host のときだけ走る"))


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """利用者のまっさらなホームフォルダー。invoice が残すものは、この中に置かれる。"""
    folder = tmp_path / "home"
    folder.mkdir()
    monkeypatch.setenv("HOME", str(folder))
    return folder


@pytest.fixture
def ledger(tmp_path: Path) -> Callable[..., Path]:
    """明細の中身を、利用者が保存するとおりのファイルにして、そのパスを返す。"""

    def write(text: str, name: str = "2026年11月分明細.csv", encoding: str = "utf-8") -> Path:
        path = tmp_path / name
        path.write_bytes(text.encode(encoding))
        return path

    return write


@pytest.fixture
def terminal(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Terminal]:
    """利用者が端末で打つ答えを、順に渡す代役を置く。"""

    def answering(*answers: str) -> Terminal:
        double = Terminal(answers)
        monkeypatch.setattr(sys, "stdin", double)
        return double

    return answering


@pytest.fixture
def printer(monkeypatch: pytest.MonkeyPatch) -> Printer:
    """既定のプリンターの代役を、printing.send に替えて置く。"""
    double = Printer()
    monkeypatch.setattr(printing, "send", double.send)
    return double


@pytest.fixture
def aoba(home: Path) -> Issuer:
    """ガイドの答えで、株式会社あおば事務用品の発行者情報を残したあとのホームフォルダー。"""
    return save_aoba()
