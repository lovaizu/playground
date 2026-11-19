"""Checks the trace between invoicer's architecture and its tests: `python3 tests/trace.py`.

Each test states, in its docstring's first line, `Supports: <name>, <name>`, and then its Given,
When, and Then. An E2E case of tests/test_e2e.py names key results; an integration case of
tests/test_integration.py names the architecture's stories, branches, principle items,
components, and data; each other case names an integration case as `<Class>.<test>`.

Gives 0 where every key result has an E2E case, every element an integration case, and every name
a case gives exists; 1 with a line for each one that doesn't."""

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

KEY_RESULTS = ["KR1.1", "KR1.2", "KR2.1"]

# The architecture's elements, as its Stories, Sequences, Principles, Components, and Data model
# name them.
ELEMENTS = [
    "S1",
    "S2",
    "S3",
    "S4",
    "S2: rate wrong",
    "S2: file missing",
    "S2: not an .ods",
    "S2: label missing",
    "S2: header missing",
    "S2: cell wrong",
    "S2: no lines",
    "S2: no printer",
    "P1",
    "P2",
    "P3",
    "P4",
    "P5",
    "Command",
    "Sheet reader",
    "Rate reader",
    "Invoice page",
    "Printer",
    "Library",
    "Sheet file",
    "Invoice details",
    "Lines",
    "Rate",
    "Refusal",
]


def cases(path):
    """Each test of the file at path, as (Class.test, docstring)."""
    with open(path, encoding="utf-8") as source:
        tree = ast.parse(source.read())
    found = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test"):
                    found.append((f"{node.name}.{item.name}", ast.get_docstring(item) or ""))
    return found


def supports(doc):
    """The names that a docstring's `Supports:` line gives, or None where it has none."""
    first = doc.splitlines()[0] if doc else ""
    if not first.startswith("Supports: "):
        return None
    return [name.strip() for name in first[len("Supports: ") :].split(",") if name.strip()]


def check(folder):
    """Each fault of the trace in the tests of folder, a line each."""
    faults = []
    files = sorted(name for name in os.listdir(folder) if name.startswith("test_") and name.endswith(".py"))
    found = {name: cases(os.path.join(folder, name)) for name in files}
    integration = {case for case, _ in found.get("test_integration.py", [])}
    reached = {"test_e2e.py": set(), "test_integration.py": set()}
    for name, each in found.items():
        for case, doc in each:
            where = f"{name} {case}"
            for word in ("Given ", "When ", "Then "):
                if f"\n{word}" not in f"\n{doc}":
                    faults.append(f"{where}: its docstring states no {word.strip()}")
            names = supports(doc)
            if not names:
                faults.append(f"{where}: its docstring opens with no `Supports:` line")
                continue
            known = {"test_e2e.py": KEY_RESULTS, "test_integration.py": ELEMENTS}.get(name, integration)
            for each_name in names:
                if each_name not in known:
                    faults.append(f"{where}: supports `{each_name}`, which isn't one level up")
                elif name in reached:
                    reached[name].add(each_name)
    for kr in KEY_RESULTS:
        if kr not in reached["test_e2e.py"]:
            faults.append(f"{kr}: no E2E case names it")
    for element in ELEMENTS:
        if element not in reached["test_integration.py"]:
            faults.append(f"{element}: no integration case names it")
    return faults


def main():
    faults = check(HERE)
    for fault in faults:
        print(fault)
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
