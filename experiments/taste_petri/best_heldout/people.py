"""Every person benchmarked on held-out preference data: best profile minus its own baseline, one chart.

Run from experiments/taste_petri after make.py: `python3 best_heldout/people.py`. No model calls. Rows whose numbers live
outside this checkout are quoted from the cited source; the Hobbhahn development row is recomputed from its predictions.
"""
import json
import random
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
owain = json.load(open(HERE / "results.json"))["tests"]["M0s/p"]


def gio_dev_row():
    """Hobbhahn development choices (Gio's full-history run): best method minus no history, item bootstrap."""
    src = "origin/codex/gio-full-history:results/fidelity/hobbhahn-full-paper-05/predictions.jsonl"
    rows = [json.loads(x) for x in subprocess.run(["git", "show", src], capture_output=True, text=True,
                                                   check=True).stdout.splitlines()]
    by = {}
    for r in rows:
        by.setdefault(r["method"], {})[r["example_id"]] = float(r["correct"])
    ids = sorted(by["m0"])
    best = max(["m1", "m2", "m3"], key=lambda m: sum(by[m].values()))
    d = [by[best][i] - by["m0"][i] for i in ids]
    rng = random.Random(0)
    bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(4000))
    return best, 100 * sum(d) / len(d), 100 * bs[200], 100 * bs[3800], len(ids)


best, g, glo, ghi, gn = gio_dev_row()
assert best == "m3", best  # the label below names ICAI principles
# (person, profile, detail line, diff, lo, hi, source)
ROWS = [
    ("Owain Evans", "Informal-writing persona",
     "96 pairs from his 2026 work · probability on his choice · vs no profile",
     100 * owain["S_inf"]["diff"], *(100 * x for x in owain["S_inf"]["ci90"]), "best_heldout/results.json"),
    ("Owain Evans", "Contrastive card",
     "same 96 pairs · probability on his choice · vs no profile",
     100 * owain["P4"]["diff"], *(100 * x for x in owain["P4"]["ci90"]), "best_heldout/results.json"),
    ("Ethan Cai", "His 16 past answers in the prompt",
     "only 4 test questions · probability on his choice · vs no history",
     9.0, 3.0, 15.0, "commit 2aed15e6 (data/researchers/ethan_cai/usermodel.json)"),
    ("Marius Hobbhahn", "Persona fitted on his papers",
     "58 pairs from his recent work · probability on his choice · vs no profile",
     -2.9, -5.9, 0.1, "synthme_hobbhahn/results.md"),
    ("Marius Hobbhahn", "Principles from his history",
     f"{gn} choices, labels inferred by AI · accuracy · vs no history",
     g, glo, ghi, "origin/codex/gio-full-history results/fidelity/hobbhahn-full-paper-05"),
    ("64 PRISM raters", "Each rater's own history",
     "crowd ratings of chatbot replies, pooled · accuracy · vs another rater's history",
     -1.83, -5.75, 2.08, "origin/codex/gio-morning-04 docs/overnight/gio-profile-20261115/control/MORNING_SUMMARY.md"),
]
json.dump([dict(zip(["person", "profile", "detail", "diff_pts", "lo", "hi", "source"], r)) for r in ROWS],
          open(HERE / "people.json", "w"), indent=1)

STYLE = ('<style>.bg{fill:#fcfcfb}.t1{fill:#0b0b0b}.t2{fill:#52514e}.grid{stroke:#e4e3df}.ref{stroke:#8a8984}'
         '.up{fill:#2a78d6;stroke:#2a78d6}.down{fill:#eb6834;stroke:#eb6834}.flat{fill:#8a8984;stroke:#8a8984}'
         '.ring{stroke:#fcfcfb}@media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.t1{fill:#f0efec}'
         '.t2{fill:#c3c2b7}.grid{stroke:#383835}.up{fill:#3987e5;stroke:#3987e5}.down{fill:#d95926;stroke:#d95926}'
         '.ring{stroke:#1a1a19}}</style>')
W, L, R, TOP, ROW = 980, 400, 760, 104, 62
H = TOP + ROW * len(ROWS) + 70
lo_x, hi_x = -12, 16


def x(v):
    return L + (v - lo_x) / (hi_x - lo_x) * (R - L)


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">', STYLE,
       f'<rect class="bg" width="{W}" height="{H}"/>',
       '<text class="t1" x="20" y="32" font-size="17" font-weight="600">'
       'A profile helped for Owain Evans and possibly Ethan Cai, not for Marius Hobbhahn or PRISM raters</text>',
       '<text class="t2" x="20" y="54" font-size="13">Each person\'s best profile minus that benchmark\'s own baseline, '
       'in percentage points · whiskers: 90% interval (raters: 95%)</text>',
       '<text class="t2" x="20" y="72" font-size="13">Blue: interval above zero · orange: below zero · '
       'gray: includes zero. Metrics and baselines differ by row, so compare signs, not sizes.</text>']
axis_y = TOP + ROW * len(ROWS) - 18
for v in range(lo_x, hi_x + 1, 4):
    cls, dash = ("ref", ' stroke-dasharray="4 4"') if v == 0 else ("grid", "")
    svg.append(f'<line class="{cls}" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{TOP - 16}" y2="{axis_y}"{dash}/>')
    svg.append(f'<text class="t2" x="{x(v):.1f}" y="{axis_y + 18}" font-size="12" text-anchor="middle">{v:+d}</text>')
svg.append(f'<text class="t2" x="{x(0) - 6:.1f}" y="{axis_y + 36}" font-size="12" text-anchor="end">profile hurt</text>'
           f'<text class="t2" x="{x(0) + 6:.1f}" y="{axis_y + 36}" font-size="12">profile helped</text>')
for i, (person, profile, detail, d, lo, hi, _) in enumerate(ROWS):
    y = TOP + ROW * i + 6
    cls = "up" if lo > 0 else "down" if hi < 0 else "flat"
    svg.append(f'<text class="t1" x="{L - 16}" y="{y - 4}" font-size="13" text-anchor="end"><tspan font-weight="600">'
               f'{person}</tspan> · {profile}</text>')
    svg.append(f'<text class="t2" x="{L - 16}" y="{y + 12}" font-size="11" text-anchor="end">{detail}</text>')
    svg.append(f'<line class="{cls}" x1="{x(lo):.1f}" x2="{x(hi):.1f}" y1="{y}" y2="{y}" stroke-width="2" '
               'stroke-linecap="round"/>')
    svg.append(f'<circle class="{cls} ring" cx="{x(d):.1f}" cy="{y}" r="6" stroke-width="2"/>'
               f'<title>{person}, {profile}: {d:+.1f} [{lo:+.1f}, {hi:+.1f}]</title>')
    svg.append(f'<text class="t1" x="{R + 16}" y="{y + 4}" font-size="13">{d:+.1f}</text>'
               f'<text class="t2" x="{R + 58}" y="{y + 4}" font-size="11">[{lo:+.1f}, {hi:+.1f}]</text>')
svg.append(f'<text class="t2" x="20" y="{H - 14}" font-size="11">Not plotted: Hobbhahn offline ranking model (68% vs a '
           'coin flip, no matched baseline); a two-researcher writing panel where every arm scored 28/28.</text>')
svg.append("</svg>")
(HERE / "people.svg").write_text("\n".join(svg) + "\n")
print(json.dumps(ROWS, indent=1))
