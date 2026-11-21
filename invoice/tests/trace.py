"""invoice のトレースを確かめる。

    python3 invoice/tests/trace.py check <invoice の一式のフォルダー>

アーキテクチャの要素ごとに結合ケースがあり、どのケースも一つ上の段の要素かケースを
名指ししているかを確かめる。不備がなければ 0、あれば不備を一行ずつ示して 1、
引数が違えば使い方を示して 2 を返す。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

USAGE = "usage: trace.py check <product>\n"


def section(text: str, heading: str) -> str:
    """見出しから、同じか上の段の次の見出しまで。"""
    level = heading.split()[0]
    start = text.index(f"\n{heading}\n")
    rest = text[start + len(heading) + 2 :]
    end = re.search(rf"^#{{1,{len(level)}}} ", rest, re.M)
    return rest[: end.start()] if end else rest


def elements(product: Path) -> tuple[set[str], set[str]]:
    """鍵となる結果の ID と、アーキテクチャの要素の名前。"""
    vision = (product / "docs" / "product-vision.md").read_text(encoding="utf-8")
    architecture = (product / "docs" / "architecture.md").read_text(encoding="utf-8")
    results = set(re.findall(r"^\s*- (KR\d+\.\d+):", vision, re.M))
    stories = set(re.findall(r"^- (S\d+):", architecture, re.M))
    principles = set(re.findall(r"^\s+- (P\d+\.\d+):", architecture, re.M))
    # データの名前は句読点を持たず、方針の行はその決まりの原則の項目で名指される。
    data = set(re.findall(r"^- ([^\s、。\[\]]+)\\$", section(architecture, "### データモデル"), re.M))
    components = set(re.findall(r"^- (\S+) \(", section(architecture, "### コンポーネント"), re.M))
    return results, stories | principles | data | components


def cases(folder: Path) -> dict[str, tuple[Path, tuple[str, ...], bool]]:
    """フォルダーの各テストを、名前から、ファイル、名指すもの、プロパティかどうかへ。"""
    found = {}
    for path in sorted(folder.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            names: tuple[str, ...] = ()
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name | ast.Attribute)
                    and (getattr(decorator.func, "id", None) or getattr(decorator.func, "attr", None)) == "supports"
                ):
                    names += tuple(str(arg.value) for arg in decorator.args if isinstance(arg, ast.Constant))
            found[node.name] = (path, names, path.name == "test_properties.py")
    return found


def faults(product: Path) -> list[str]:
    """トレースの不備を、一行ずつ。"""
    results, architecture = elements(product)
    tests = product / "tests"
    e2e, integration, unit = (cases(tests / level) for level in ("e2e", "integration", "unit"))
    found = []
    for level, named, allowed in (
        ("e2e", e2e, results),
        ("integration", integration, architecture),
    ):
        for name, (path, names, _) in named.items():
            if not names:
                found.append(f"{path}: {name}: 何も名指ししていない")
            for each in names:
                if each not in allowed:
                    found.append(f"{path}: {name}: {each} は {level} の一つ上の段にない")
    for name, (path, names, property_) in unit.items():
        allowed = architecture if property_ else set(integration)
        if not names:
            found.append(f"{path}: {name}: 何も名指ししていない")
        for each in names:
            if each not in allowed:
                found.append(f"{path}: {name}: {each} は一つ上の段にない")
    reached = {each for _, names, _ in integration.values() for each in names}
    found += [f"{tests / 'integration'}: {each} を名指す結合ケースがない" for each in sorted(architecture - reached)]
    covered = {each for _, names, _ in e2e.values() for each in names}
    found += [f"{tests / 'e2e'}: {each} を名指す E2E ケースがない" for each in sorted(results - covered)]
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "check":
        sys.stderr.write(USAGE)
        return 2
    found = faults(Path(argv[1]))
    for each in found:
        print(each)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
