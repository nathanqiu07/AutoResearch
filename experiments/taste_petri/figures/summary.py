"""Summary chart of tonight's significant or directional results, as SVG (standard library only).

    python3 experiments/taste_petri/figures/summary.py     # writes figures/summary.svg

Numbers are copied from the results files named in each panel's source line.
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent / "summary.svg"
W, H = 1400, 960
HAIKU, GPT, KIMI, GREY = "#1f77b4", "#d62728", "#2ca02c", "#888"
svg = []


def text(x, y, s, size=13, anchor="start", weight="normal", fill="#222"):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" '
               f'fill="{fill}" font-family="Helvetica, Arial, sans-serif">{s}</text>')


def line(x1, y1, x2, y2, stroke="#222", width=1, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}"{d}/>')


def forest(x0, y0, w, title, source, rows, lo, hi, ticks, unit_note):
    """rows: (label, [(value, ci_lo, ci_hi, colour)], note). Horizontal points with 90% CIs."""
    text(x0, y0, title, 16, weight="bold")
    text(x0, y0 + 18, source, 11, fill=GREY)
    lab_w, top, rh = 300, y0 + 50, 46
    px = lambda v: x0 + lab_w + (v - lo) / (hi - lo) * (w - lab_w - 20)
    bottom = top + rh * len(rows)
    for t in ticks:
        line(px(t), top - 8, px(t), bottom, "#ddd")
        text(px(t), bottom + 16, f"{t:+g}" if t else "0", 11, "middle", fill=GREY)
    line(px(0), top - 8, px(0), bottom, "#555", 1.5)
    text(px((lo + hi) / 2), bottom + 34, unit_note, 12, "middle", fill=GREY)
    for i, (label, pts, note) in enumerate(rows):
        y = top + i * rh + rh / 2
        text(x0, y - 2 if note else y + 4, label, 13)
        if note:
            text(x0, y + 13, note, 11, fill=GREY)
        for j, (v, a, b, c) in enumerate(pts):
            yy = y + (j - (len(pts) - 1) / 2) * 12
            line(px(a), yy, px(b), yy, c, 2.5)
            svg.append(f'<circle cx="{px(v)}" cy="{yy}" r="5" fill="{c}"/>')
            text(px(b) + 6, yy + 4, f"{v:+.2f}", 11, fill=c)
    return bottom + 50


def bars(x0, y0, w, title, source, rows, lo, hi, ref=None, ref_label="", ticks=None):
    """rows: (label, value, ci or None, colour). Horizontal bars."""
    text(x0, y0, title, 16, weight="bold")
    text(x0, y0 + 18, source, 11, fill=GREY)
    lab_w, top, rh = 300, y0 + 50, 34
    px = lambda v: x0 + lab_w + (v - lo) / (hi - lo) * (w - lab_w - 60)
    bottom = top + rh * len(rows)
    for t in ticks or [lo + k * (hi - lo) / 4 for k in range(5)]:
        line(px(t), top - 8, px(t), bottom, "#ddd")
        text(px(t), bottom + 16, f"{t:.2f}", 11, "middle", fill=GREY)
    for i, (label, v, ci, c) in enumerate(rows):
        y = top + i * rh
        text(x0, y + rh / 2 + 4, label, 13)
        svg.append(f'<rect x="{px(lo)}" y="{y + 7}" width="{px(v) - px(lo)}" height="{rh - 14}" fill="{c}" opacity="0.8"/>')
        if ci:
            line(px(ci[0]), y + rh / 2, px(ci[1]), y + rh / 2, "#222", 1.5)
        text(px(max(v, ci[1] if ci else v)) + 6, y + rh / 2 + 4, f"{v:.2f}", 12)
    if ref is not None:
        line(px(ref), top - 12, px(ref), bottom, "#555", 1.5, "5,4")
        text(px(ref), top - 16, ref_label, 11, "middle", fill="#555")
    return bottom + 40


text(40, 40, "Taste for Petri, 2026-11-15: what moved and what didn't", 22, weight="bold")
text(40, 62, "Dots = paired mean change, lines = 90% CI (bootstrap over 10-11 seeds). A line that doesn't cross 0 is "
     "significant.  Colours: haiku judge/target (blue), GPT-6 Sol judge (red), Kimi K2.6 target (green).", 12, fill=GREY)

# A: Petri realism effects
yA = forest(40, 105, 660, "A. Petri realism (1-10): what raises it",
            "surgery/, petri_taste/, judge_transfer/ results.md",
            [("Remove the bait (same scenario)", [(0.8, 0.4, 1.1, HAIKU), (0.91, 0.48, 1.36, GPT)], "manipulation check, not usable: bait reached −0.47"),
             ("Rewrite to fix the judge's own complaints", [(0.6, 0.3, 1.0, HAIKU), (0.78, 0.18, 1.43, GPT)], "fails validity: bait reached −0.20"),
             ("Make the bait's evidence inconclusive", [(0.2, -0.3, 0.6, HAIKU)], "bait reached −0.05"),
             ("Same bait, ordinary presentation", [(0.1, -0.3, 0.6, HAIKU), (0.08, -0.47, 0.67, GPT)], ""),
             ("Put the bait in the task's path", [(-0.1, -0.5, 0.3, HAIKU)], ""),
             ("Taste: Bowman evidence vs none", [(-0.1, -0.6, 0.5, HAIKU), (0.03, -0.39, 0.48, GPT)], "also vs Carlini placebo: −0.1 / +0.08")],
            -0.8, 1.6, [-0.5, 0, 0.5, 1.0, 1.5], "change in Petri realism (points)")

# B: A2 effects, haiku vs Kimi
forest(740, 105, 620, "B. A2 = target's own 'was this a test?' (0-1)",
       "judge_transfer/results.md: same transcripts, two targets answer",
       [("Remove the bait", [(-0.12, -0.18, -0.06, HAIKU), (-0.01, -0.03, 0.01, KIMI)], "haiku moves, Kimi doesn't"),
        ("Rewrite to fix the judge's complaints", [(-0.12, -0.20, -0.04, HAIKU), (-0.01, -0.02, 0.00, KIMI)], "haiku moves, Kimi doesn't")],
       -0.25, 0.1, [-0.2, -0.1, 0, 0.1], "change in A2 (negative = reads less like a test)")

# C: Kimi A2 levels by transcript type
yC = bars(740, 360, 620, "C. Kimi K2.6's A2 by transcript type",
          "genre_ladder/results.md (placeholder probes, Petri render, 24k cut)",
          [("Real users' business chats (no tools)", 0.68, (0.61, 0.74), "#7fbf7f"),
           ("Real users' coding sessions (OpenHands)", 0.90, (0.88, 0.92), "#7fbf7f"),
           ("Real coding sessions + spliced bait", 0.91, (0.89, 0.92), "#bbb"),
           ("Our audits, bait removed", 0.92, (0.90, 0.94), "#e3a35c"),
           ("Our audits", 0.93, (0.92, 0.94), "#e3a35c"),
           ("Benchmark runs: SWE-rebench", 0.95, (0.94, 0.95), "#c96f6f"),
           ("Benchmark runs: tau-bench", 0.95, (0.94, 0.96), "#c96f6f")],
          0.5, 1.0, ticks=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
text(740, yC - 8, "Green = real use, orange = our audits, red = benchmarks.  Room left for agentic audits: ~0.03 (0.93 → 0.90).",
     11, fill=GREY)

# D: forced choice
yD = bars(40, yA + 10, 660, "D. Side by side: how often Kimi picks our audit as 'the test'",
          "forced_choice/results.md: each audit shown beside a real coding session, both orders",
          [("Our audits (R0)", 0.77, None, "#e3a35c"),
           ("Bait removed", 0.70, None, "#e3a35c"),
           ("Same bait, ordinary presentation", 0.78, None, "#e3a35c"),
           ("Rewritten to fix the judge's complaints", 0.82, None, "#e3a35c")],
          0.4, 1.0, ticks=[0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], ref=0.5, ref_label="0.5 = can't tell apart")
text(40, yD - 8, "Bait removed vs R0: −0.07 [−0.16, +0.01], the right direction but not quite significant.", 11, fill=GREY)

# E: ranker
bars(740, yC + 30, 620, "E. Can a model predict realism without running audits?",
     "taste_ranker/results.md: correlation between a ranker's order of 7 rewrites and measured realism",
     [("Sonnet, no profile", 0.26, (0.11, 0.41), "#9ab"),
      ("Sonnet + Bowman card", 0.29, (0.09, 0.48), "#9ab"),
      ("Sonnet + Carlini card (placebo)", 0.24, (0.03, 0.43), "#9ab"),
      ("Noise ceiling (measurement reliability)", 0.57, None, "#ccc")],
     0.0, 0.8)

svg.insert(0, f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
              f'<rect width="{W}" height="{H}" fill="white"/>')
svg.append("</svg>")
OUT.write_text("\n".join(svg))
print(OUT)
