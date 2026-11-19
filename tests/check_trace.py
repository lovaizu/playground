"""The check of the trace between the tests and the documents one level up.

Run `python3 tests/check_trace.py` from anywhere. It exits 0 where the trace holds, and 1 with one line
for each fault.

It reads each element by where the documents put its name: each key result as `KR<n>.<m>` in
docs/product-vision.md; and each story as `S<n>`, each principle item as `P<n>.<m>`, each
component, and each kind of data from docs/architecture.md. It reads each case by the line
`Supports:` of its docstring. An E2E case names key results, an integration or contract case
names elements, and a unit case names integration cases.

The trace holds where each key result has an E2E case, each element has an integration case, and
each case names only what exists.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
E2E = "test_e2e.py"
INTEGRATION = ("test_integration.py", "test_contract.py")

Case = tuple[str, int, str, list[str]]


def section(text: str, heading: str) -> str:
    """The lines under `heading` up to the next heading of its level or a higher one."""
    level = len(heading) - len(heading.lstrip("#"))
    found = re.search(
        rf"^{re.escape(heading)}\n(.*?)(?=^#{{1,{level}}} |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return found.group(1) if found else ""


def elements() -> set[str]:
    """The names of the stories, principle items, components, and data of the architecture."""
    text = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    names = set(
        re.findall(r"^- `(S\d+)`:", section(text, "## User stories"), re.MULTILINE)
    )
    names |= set(
        re.findall(
            r"^\s+- `(P\d+\.\d+)`:", section(text, "### Principles"), re.MULTILINE
        )
    )
    names |= set(
        re.findall(r"^- (.+?) \(", section(text, "### Components"), re.MULTILINE)
    )
    names |= set(
        re.findall(r"^- (\w[\w ]*)\\$", section(text, "### Data model"), re.MULTILINE)
    )
    return names


def key_results() -> set[str]:
    """The key results of the product vision."""
    text = (ROOT / "docs" / "product-vision.md").read_text(encoding="utf-8")
    return set(re.findall(r"`(KR\d+\.\d+)`:", text))


def cases() -> list[Case]:
    """Each test as its file, line, name, and the names after Supports, [] where it has none."""
    found: list[Case] = []
    for path in sorted(TESTS.glob("test_*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                said = re.search(
                    r"^Supports: (.+?)\.?$", ast.get_docstring(node) or "", re.MULTILINE
                )
                names = (
                    [name.strip() for name in said.group(1).split(",")] if said else []
                )
                found.append((path.name, node.lineno, node.name, names))
    return found


def faults() -> list[str]:
    """One line for each fault of the trace, [] where it holds."""
    every = cases()
    known: dict[str, set[str]] = {
        "key result": key_results(),
        "element": elements(),
        "integration case": {name for file, _, name, _ in every if file in INTEGRATION},
    }
    out = []
    for file, line, name, names in every:
        kind = (
            "key result"
            if file == E2E
            else "element"
            if file in INTEGRATION
            else "integration case"
        )
        if not names:
            out.append(f"tests/{file}:{line}: {name} names no {kind} after Supports:")
        out += [
            f"tests/{file}:{line}: {name} names {each!r}, which is no {kind}"
            for each in names
            if each not in known[kind]
        ]
    reached = {each for file, _, _, names in every if file == E2E for each in names}
    out += [
        f"docs/product-vision.md: {kr} has no E2E case"
        for kr in sorted(known["key result"] - reached)
    ]
    reached = {
        each for file, _, _, names in every if file == INTEGRATION[0] for each in names
    }
    out += [
        f"docs/architecture.md: {each} has no integration case"
        for each in sorted(known["element"] - reached)
    ]
    return out


def main() -> int:
    """Prints each fault, and gives 1 where there's one, or 0."""
    found = faults()
    for each in found:
        print(each)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
