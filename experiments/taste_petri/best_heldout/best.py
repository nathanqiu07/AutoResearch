"""Best result per benchmarked person: with profile vs no profile, grouped bar chart (best.svg).

Run from experiments/taste_petri: `python3 best_heldout/best.py`. No model calls.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
owain = json.load(open(HERE / "results.json"))["arms"]
marius = json.load(open(HERE / "../../lopsided_all/pref_results.json"))["heldout"]["all"]
# (person, profile, metric line, no profile, with profile)
ROWS = [
    ("Marius Hobbhahn", "Preferences fit on his non-obvious past choices",
     f"share of his {marius['n']} later choices predicted right", marius["m0"]["accuracy"], marius["m4_gated"]["accuracy"]),
    ("Owain Evans", "Persona fitted on his pre-2026 informal writing",
     "probability on his actual choice, 96 choices from his 2026 work", owain["M0s"]["p_his"], owain["S_inf"]["p_his"]),
    ("Ethan Cai", "His own 16 past answers in the prompt",
     "probability on his choice, 4 test questions", 0.54, 0.63),  # commit 2aed15e6
]
STYLE = ('<style>.bg{fill:#fcfcfb}.t1{fill:#0b0b0b}.t2{fill:#52514e}.grid{stroke:#e4e3df}'
         '.base{fill:#8a8984;stroke:#8a8984}.best{fill:#2a78d6;stroke:#2a78d6}.ring{stroke:#fcfcfb}'
         '@media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.t1{fill:#f0efec}.t2{fill:#c3c2b7}'
         '.grid{stroke:#383835}.best{fill:#3987e5;stroke:#3987e5}.ring{stroke:#1a1a19}}</style>')
W, H, TOP, BASE = 760, 420, 90, 340
GW = (W - 80) / len(ROWS)


def y(v):
    return BASE - v * (BASE - TOP)


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">', STYLE,
       f'<rect class="bg" width="{W}" height="{H}"/>',
       '<text class="t1" x="20" y="32" font-size="17" font-weight="600">A profile improves predictions of later choices</text>',
       '<rect class="base" x="20" y="48" width="12" height="12" rx="2"/><text class="t2" x="38" y="58" font-size="12">no profile</text>'
       '<rect class="best" x="120" y="48" width="12" height="12" rx="2"/><text class="t2" x="138" y="58" font-size="12">with profile</text>']
for v in [0, 0.25, 0.5, 0.75, 1.0]:
    svg.append(f'<line class="grid" x1="60" x2="{W - 20}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
               f'<text class="t2" x="52" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end">{v:.0%}</text>')
for i, (person, profile, metric, base, prof) in enumerate(ROWS):
    cx = 70 + GW * i + GW / 2
    for j, (v, cls) in enumerate([(base, "base"), (prof, "best")]):
        bx = cx - 52 + j * 54
        svg.append(f'<rect class="{cls}" x="{bx:.1f}" y="{y(v):.1f}" width="50" height="{BASE - y(v):.1f}" rx="3"/>'
                   f'<text class="{"t1" if j else "t2"}" x="{bx + 25:.1f}" y="{y(v) - 6:.1f}" font-size="13" '
                   f'text-anchor="middle"{" font-weight=\"600\"" if j else ""}>{v:.0%}</text>')
    svg.append(f'<text class="t1" x="{cx:.1f}" y="{BASE + 22}" font-size="14" font-weight="600" text-anchor="middle">{person}</text>'
               f'<text class="t2" x="{cx:.1f}" y="{BASE + 40}" font-size="11" text-anchor="middle">{metric.split(",")[0]}</text>')
svg.append("</svg>")
(HERE / "best.svg").write_text("\n".join(svg) + "\n")
print([(r[0], r[3], r[4]) for r in ROWS])
