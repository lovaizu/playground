"""The trace from the design to the tests: each element has a test that names it, and each test
names an element or a case, on its docstring's line `Traces: <name>, <name>.`"""

from __future__ import annotations

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The stories, the principles, and the components.
ELEMENTS = ("S1", "S2", "P1", "P2", "P3", "command", "sheet reader", "render")
# The cases of the test design that the tests carry out.
CASES = ("I-S1", "I-S2-rate", "I-S2-sheet", "I-P1", "I-P3", "I-print", "U-read_lines", "U-main", "Property", "Trace")


def traces():
    """Each test of tests/ by its id, with the names on its Traces line."""
    suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, "tests"), top_level_dir=ROOT)
    found = {}
    pending = [suite]
    while pending:
        each = pending.pop()
        if isinstance(each, unittest.TestSuite):
            pending.extend(each)
            continue
        doc = getattr(each, each.id().rsplit(".", 1)[1]).__doc__ or ""
        line = next((text.strip() for text in doc.splitlines() if text.strip().startswith("Traces:")), "Traces:")
        found[each.id()] = [name.strip() for name in line[len("Traces:"):].rstrip(".").split(",") if name.strip()]
    return found


class Trace(unittest.TestCase):
    def test_trace_each_element_has_a_test_naming_it(self):
        """Given the tests of tests/,
        when their Traces lines are read,
        then each story, principle, and component is named by at least one test.

        Traces: Trace.
        """
        named = {name for names in traces().values() for name in names}

        self.assertEqual([element for element in ELEMENTS if element not in named], [], "elements no test names")

    def test_trace_each_test_names_only_known_elements_or_cases_and_at_least_one(self):
        """Given the tests of tests/,
        when their Traces lines are read,
        then each test names at least one element or case, and nothing that is neither.

        Traces: Trace.
        """
        known = set(ELEMENTS) | set(CASES)

        unnamed = [test for test, names in traces().items() if not names]
        unknown = {test: names for test, names in traces().items() if set(names) - known}

        self.assertEqual(unnamed, [], "tests that name no element or case")
        self.assertEqual(unknown, {}, "tests that name what is neither an element nor a case")
