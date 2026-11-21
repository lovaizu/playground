"""置き場 (place.folder) の単体ケース。"""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice import place

supports = pytest.mark.supports


@supports("test_どのフォルダーで打っても同じ発行者情報と番号を使う")
def test_置き場はホームフォルダーの中にありどのフォルダーで打っても同じ(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: 二つのフォルダー。
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    # When
    monkeypatch.chdir(first)
    here = place.folder()
    monkeypatch.chdir(second)
    there = place.folder()
    # Then
    assert here == there
    assert here.is_relative_to(home) and here != home
    assert not here.exists()


@supports("test_どのフォルダーで打っても同じ発行者情報と番号を使う")
def test_置き場は利用者のホームフォルダーに従う(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: 別の利用者のホームフォルダー。
    other = tmp_path / "other"
    other.mkdir()
    mine = place.folder()
    # When
    monkeypatch.setenv("HOME", str(other))
    theirs = place.folder()
    # Then
    assert theirs.is_relative_to(other)
    assert theirs != mine
