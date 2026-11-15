import io
import os
import unittest
from unittest import mock

from autoresearch.ui import Console, strip_ansi, visible_len


class _TTY(io.StringIO):
    encoding = "utf-8"

    def isatty(self):
        return True


class ConsoleTest(unittest.TestCase):
    def test_color_off_for_pipes_and_no_color(self):
        self.assertFalse(Console(io.StringIO()).color)
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertFalse(Console(_TTY()).color)
        with mock.patch.dict(os.environ, {"FORCE_COLOR": "1", "NO_COLOR": ""}):
            self.assertTrue(Console(io.StringIO()).color)

    def test_style_is_plain_without_color(self):
        c = Console(io.StringIO(), color=False)
        self.assertEqual(c.style("x", "bold", "red"), "x")
        c = Console(io.StringIO(), color=True)
        self.assertEqual(strip_ansi(c.style("x", "bold", "red")), "x")
        self.assertNotEqual(c.style("x", "bold"), "x")

    def test_ascii_fallback(self):
        s = io.StringIO()   # no encoding attribute value -> ASCII box
        c = Console(s, color=False)
        self.assertTrue(all(ord(ch) < 128 for ch in c.panel(["hello"], title="T")))

    def test_table_columns_align(self):
        c = Console(io.StringIO(), color=True, unicode=True, width=100)
        t = c.table(["a", "bee"], [[c.style("1", "green"), "22"], ["333", c.style("4", "red")]], align="<>")
        widths = {visible_len(line) for line in t.splitlines()}
        self.assertEqual(len(widths), 1, t)

    def test_table_shrinks_flex_column_to_width(self):
        c = Console(io.StringIO(), color=False, unicode=True, width=60)
        t = c.table(["id", "text"], [["f1", "x" * 200]], flex=1)
        self.assertTrue(all(visible_len(line) <= 60 for line in t.splitlines()), t)
        self.assertEqual(t.count("x"), 200 + 1)   # wrapped, nothing lost (+1 for the "x" in "text")
        t = c.table(["id", "text"], [["f1", "x" * 200]], flex=1, wrap=False)
        self.assertTrue(all(visible_len(line) <= 60 for line in t.splitlines()), t)
        self.assertIn("…", t)

    def test_panel_lines_same_width(self):
        c = Console(io.StringIO(), color=True, unicode=True, width=80)
        p = c.panel(["short", c.style("a longer styled line", "bold"), "y" * 300], title="Run")
        self.assertEqual(len({visible_len(line) for line in p.splitlines()}), 1, p)

    def test_multiline_cells_and_wrapping(self):
        c = Console(io.StringIO(), color=True, unicode=True, width=50)
        t = c.table(["id", "text"], [["f1", [c.style("cat", "cyan"), "word " * 30]]], flex=1)
        lines = t.splitlines()
        self.assertEqual(len({visible_len(line) for line in lines}), 1, t)
        self.assertGreater(len(lines), 6)          # header, rules, category line and wrapped text
        self.assertIn(c.style("cat", "cyan"), t)    # a short line keeps its colour

    def test_bar(self):
        c = Console(io.StringIO(), color=False, unicode=True)
        self.assertEqual(c.bar(0.5, width=4), "██░░")
        self.assertEqual(c.bar(None, width=3), "░░░")
        self.assertEqual(c.bar(7, width=2), "██")


if __name__ == "__main__":
    unittest.main()
