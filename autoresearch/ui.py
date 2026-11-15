"""Terminal formatting for the CLI: colours, rules, panels and tables (standard library only).

Colour is on only when the stream is a terminal. ``NO_COLOR`` turns it off and
``FORCE_COLOR`` turns it on (https://no-color.org). Box drawing falls back to
ASCII when the stream's encoding can't print it, so piped or logged output
stays readable.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from typing import IO, List, Optional, Sequence

_CODES = {
    "bold": "1", "dim": "2", "italic": "3", "underline": "4",
    "red": "31", "green": "32", "yellow": "33", "blue": "34", "magenta": "35", "cyan": "36",
    "gray": "90", "bright_red": "91", "bright_green": "92", "bright_yellow": "93",
    "bright_blue": "94", "bright_magenta": "95", "bright_cyan": "96", "white": "97",
}
_ANSI = re.compile(r"\x1b\[[0-9;]*m")

_UNICODE_BOX = {"h": "─", "v": "│", "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯",
                "lt": "├", "rt": "┤", "tt": "┬", "bt": "┴", "x": "┼", "bar": "█", "bar_bg": "░",
                "arrow": "→", "ellipsis": "…", "bullet": "•", "ok": "✓", "no": "✗"}
_ASCII_BOX = {"h": "-", "v": "|", "tl": "+", "tr": "+", "bl": "+", "br": "+",
              "lt": "+", "rt": "+", "tt": "+", "bt": "+", "x": "+", "bar": "#", "bar_bg": ".",
              "arrow": "->", "ellipsis": "...", "bullet": "*", "ok": "y", "no": "n"}


def visible_len(s: str) -> int:
    """Printed width of ``s``, ignoring ANSI escape codes."""
    return len(_ANSI.sub("", s))


def strip_ansi(s: str) -> str:
    return _ANSI.sub("", s)


def _wants_color(stream: IO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("TERM") == "dumb":
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def _can_unicode(stream: IO) -> bool:
    enc = (getattr(stream, "encoding", None) or "").lower()
    if not enc:
        return False
    try:
        "".join(_UNICODE_BOX.values()).encode(enc)
        return True
    except (LookupError, UnicodeEncodeError):
        return False


class Console:
    """Writes styled text to one stream. Every method also works with colour off."""

    def __init__(self, stream: Optional[IO] = None, color: Optional[bool] = None,
                 unicode: Optional[bool] = None, width: Optional[int] = None):
        self.stream = stream if stream is not None else sys.stdout
        self.color = _wants_color(self.stream) if color is None else color
        self.box = _UNICODE_BOX if (_can_unicode(self.stream) if unicode is None else unicode) else _ASCII_BOX
        self.width = width or min(max(shutil.get_terminal_size((100, 24)).columns, 60), 120)

    # -- text ---------------------------------------------------------------
    def style(self, text, *styles: str) -> str:
        text = str(text)
        codes = [_CODES[s] for s in styles if s]
        if not self.color or not codes:
            return text
        return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"

    def print(self, *parts, sep: str = " ") -> None:
        self.stream.write(sep.join(str(p) for p in parts) + "\n")
        self.stream.flush()

    def truncate(self, text: str, width: int) -> str:
        """Shorten plain text to ``width`` printed characters."""
        text = str(text)
        if len(text) <= width:
            return text
        ell = self.box["ellipsis"]
        return text[: max(width - len(ell), 0)] + ell if width > len(ell) else text[:width]

    def pad(self, text: str, width: int, align: str = "<") -> str:
        gap = max(width - visible_len(text), 0)
        if align == ">":
            return " " * gap + text
        if align == "^":
            return " " * (gap // 2) + text + " " * (gap - gap // 2)
        return text + " " * gap

    def bar(self, frac: Optional[float], width: int = 10, style: str = "cyan") -> str:
        """A horizontal bar for a value in [0, 1]."""
        if frac is None:
            return self.style(self.box["bar_bg"] * width, "dim")
        f = min(max(float(frac), 0.0), 1.0)
        full = int(round(f * width))
        return self.style(self.box["bar"] * full, style) + self.style(self.box["bar_bg"] * (width - full), "dim")

    # -- blocks -------------------------------------------------------------
    def rule(self, title: str = "", style: str = "cyan") -> str:
        h = self.box["h"]
        if not title:
            return self.style(h * self.width, style)
        lead = h * 2 + " "
        head = lead + self.style(title, "bold") + " "
        return self.style(lead, style) + self.style(title, "bold", style) + " " + \
            self.style(h * max(self.width - visible_len(head), 0), style)

    def panel(self, lines: Sequence[str], title: str = "", style: str = "cyan") -> str:
        """Lines in a rounded box sized to the content (at most the console width)."""
        b = self.box
        inner = min(max([visible_len(x) for x in lines] + [visible_len(title) + 2, 20]), self.width - 4)
        top_fill = inner + 2
        if title:
            t = " " + title + " "
            top = (self.style(b["tl"] + b["h"], style) + self.style(t, "bold", style)
                   + self.style(b["h"] * max(top_fill - 1 - visible_len(t), 0) + b["tr"], style))
        else:
            top = self.style(b["tl"] + b["h"] * top_fill + b["tr"], style)
        side = self.style(b["v"], style)
        body = [f"{side} {self.pad(self._fit(x, inner), inner)} {side}" for x in lines]
        bottom = self.style(b["bl"] + b["h"] * top_fill + b["br"], style)
        return "\n".join([top] + body + [bottom])

    def _fit(self, line: str, width: int) -> str:
        if visible_len(line) <= width:
            return line
        return self.truncate(strip_ansi(line), width)   # losing colour beats breaking the box

    def kv(self, pairs: Sequence[tuple], key_style: str = "gray") -> List[str]:
        """Aligned ``key  value`` lines."""
        pairs = [(k, v) for k, v in pairs if v is not None]
        w = max([visible_len(str(k)) for k, _ in pairs] + [0])
        return [self.pad(self.style(k, key_style), w) + "  " + str(v) for k, v in pairs]

    def table(self, headers: Sequence[str], rows: Sequence[Sequence], align: Optional[str] = None,
              flex: Optional[int] = None, title: str = "", style: str = "gray") -> str:
        """A boxed table. ``align`` is one of ``<>^`` per column; ``flex`` names the
        column (plain text) that is shortened when the table is wider than the console."""
        n = len(headers)
        align = (align or "<" * n).ljust(n, "<")
        cells = [[str(c) if c is not None else "" for c in r] for r in rows]
        widths = [max([visible_len(h) for h in [headers[i]]] + [visible_len(r[i]) for r in cells]) for i in range(n)]
        total = sum(widths) + 3 * n + 1
        if flex is not None and total > self.width:
            widths[flex] = max(widths[flex] - (total - self.width), max(visible_len(headers[flex]), 8))
            cells = [r[:flex] + [r[flex] if visible_len(r[flex]) <= widths[flex]
                                 else self.truncate(strip_ansi(r[flex]), widths[flex])] + r[flex + 1:]
                     for r in cells]
        b = self.box
        line = lambda l, m, r: self.style(l + m.join(b["h"] * (w + 2) for w in widths) + r, style)
        side = self.style(b["v"], style)
        fmt = lambda r, hdr=False: side + side.join(
            " " + self.pad(self.style(c, "bold") if hdr else c, widths[i], align[i]) + " "
            for i, c in enumerate(r)) + side
        out = []
        if title:
            out.append(self.style(title, "bold"))
        out += [line(b["tl"], b["tt"], b["tr"]), fmt(list(headers), hdr=True), line(b["lt"], b["x"], b["rt"])]
        out += [fmt(r) for r in cells]
        out.append(line(b["bl"], b["bt"], b["br"]))
        return "\n".join(out)
