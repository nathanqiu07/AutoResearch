"""Best held-out preference results on e2_v4's 96 post-T Owain pairs: re-score, test, and draw one chart.

Run from experiments/taste_petri: `python3 best_heldout/make.py`. Reads cached predictions only; no model calls.
Eligible arms were fixed before scoring: pre-T material only, never tuned on post-T pairs.
"""
import itertools
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
pp = json.load(open("e2_v4/results.json"))["per_pair"]
arms = {a: {k: v[a] for k, v in pp.items()} for a in ["M0s", "NAME", "P1", "P4"]}
for name, f in [("S_inf", "synthme/test_S_inf.json"), ("S_paper", "synthme/test_S_paper.json"),
                ("P4_rerun", "e2_climb/confirm_A.json")]:  # climb A accepted no step, so H_A is P4 re-run
    arms[name] = {p["pair_id"]: p for p in json.load(open(f))["predictions"]}
ids = sorted(pp)
work = {k: pp[k]["work"] for k in ids}
works = sorted(set(work.values()))
n_in = {w: sum(work[k] == w for k in ids) for w in works}


def score(a, k, m):
    p = arms[a][k]
    return float(p["correct"]) if m == "acc" else sum(p["p_his"]) / 2


def by_work(a, b, m):
    d = dict.fromkeys(works, 0.0)
    for k in ids:
        d[work[k]] += score(a, k, m) - (score(b, k, m) if b else 0)
    return d


def mean(a, b, m):
    return sum(by_work(a, b, m).values()) / len(ids)


def boot(a, b, m, reps=4000):
    rng, d, out = random.Random(0), by_work(a, b, m), []
    for _ in range(reps):
        s = [rng.choice(works) for _ in works]
        out.append(sum(d[w] for w in s) / sum(n_in[w] for w in s))
    out.sort()
    return out[int(.05 * reps)], out[int(.95 * reps)]


def perm_p(a, b, m):
    """Exact one-sided sign-flip test over works."""
    d = list(by_work(a, b, m).values())
    obs = sum(d)
    hits = sum(sum(s * x for s, x in zip(signs, d)) >= obs - 1e-12
               for signs in itertools.product([1, -1], repeat=len(d)))
    return hits / 2 ** len(d)


ELIGIBLE = ["NAME", "P1", "P4", "S_paper", "S_inf", "P4_rerun"]
tests = {}
for base in ["M0s", "NAME"]:
    for m in ["acc", "p"]:
        cands = [a for a in ELIGIBLE if a != base]
        tests[f"{base}/{m}"] = {a: {"diff": round(mean(a, base, m), 3), "ci90": [round(x, 3) for x in boot(a, base, m)],
                                    "perm_p": round(perm_p(a, base, m), 4)} for a in cands}
summary = {a: {"acc": round(mean(a, None, "acc"), 3), "p_his": round(mean(a, None, "p"), 3),
               "p_his_ci90": [round(x, 3) for x in boot(a, None, "p")]} for a in arms}
retest = {m: {"diff": round(mean("P4_rerun", "P4", m), 3), "ci90": [round(x, 3) for x in boot("P4_rerun", "P4", m)]}
          for m in ["acc", "p"]}
json.dump({"n_pairs": len(ids), "n_works": len(works), "arms": summary, "tests": tests, "retest_P4": retest},
          open(HERE / "results.json", "w"), indent=1)

STYLE = ('<style>.bg{fill:#fcfcfb}.t1{fill:#0b0b0b}.t2{fill:#52514e}.grid{stroke:#e4e3df}.ref{stroke:#8a8984}'
       '.base{fill:#8a8984;stroke:#8a8984}.best{fill:#2a78d6;stroke:#2a78d6}.ring{stroke:#fcfcfb}'
       '@media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.t1{fill:#f0efec}.t2{fill:#c3c2b7}'
       '.grid{stroke:#383835}.ref{stroke:#8a8984}.base{fill:#8a8984;stroke:#8a8984}'
       '.best{fill:#3987e5;stroke:#3987e5}.ring{stroke:#1a1a19}}</style>')

# Chart: mean p(his choice), 90% CI over works; baselines gray, the two best profiles blue.
ROWS = [("M0s", "No profile", "", False), ("NAME", "Name only", "", False),
        ("P4", "Contrastive card", "where he departs from standard practice", True),
        ("S_inf", "Informal-writing persona", "fitted on his pre-2026 posts, podcasts, threads", True)]
W, H, L, R, TOP, ROW = 940, 380, 290, 600, 100, 58
NOTE_X = R + 24
lo_x, hi_x = 0.30, 0.55


def x(v):
    return L + (v - lo_x) / (hi_x - lo_x) * (R - L)


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">',
       STYLE,
       f'<rect class="bg" width="{W}" height="{H}"/>',
       '<text class="t1" x="20" y="32" font-size="17" font-weight="600">'
       'Profiles built from pre-2026 material predict Owain Evans’s later choices better</text>',
       '<text class="t2" x="20" y="54" font-size="13">Mean probability given to his actual choice, '
       '96 held-out 2026 decisions from 10 works · whiskers: 90% interval over works</text>']
axis_y = TOP + ROW * len(ROWS) - 14
for v in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55]:
    cls = "ref" if v == 0.5 else "grid"
    dash = ' stroke-dasharray="4 4"' if v == 0.5 else ""
    svg.append(f'<line class="{cls}" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{TOP - 20}" y2="{axis_y}"{dash}/>')
    svg.append(f'<text class="t2" x="{x(v):.1f}" y="{axis_y + 18}" font-size="12" text-anchor="middle">{v:.2f}</text>')
svg.append(f'<text class="t2" x="{x(0.5) + 4:.1f}" y="{TOP - 24}" font-size="11">coin flip</text>')
for i, (arm, label, sub, best) in enumerate(ROWS):
    y = TOP + ROW * i + 8
    s = summary[arm]
    lo, hi = s["p_his_ci90"]
    cls = "best" if best else "base"
    weight = ' font-weight="600"' if best else ""
    svg.append(f'<text class="{"t1" if best else "t2"}" x="{L - 16}" y="{y + (0 if sub else 4)}" font-size="13" '
               f'text-anchor="end"{weight}>{label}</text>')
    if sub:
        svg.append(f'<text class="t2" x="{L - 16}" y="{y + 16}" font-size="11" text-anchor="end">{sub}</text>')
    svg.append(f'<line class="{cls}" x1="{x(lo):.1f}" x2="{x(hi):.1f}" y1="{y}" y2="{y}" stroke-width="2" '
               'stroke-linecap="round"/>')
    svg.append(f'<circle class="{cls} ring" cx="{x(s["p_his"]):.1f}" cy="{y}" r="6" stroke-width="2"/>'
               f'<title>{label}: {s["p_his"]:.3f} [{lo:.3f}, {hi:.3f}]</title>')
    svg.append(f'<text class="{"t1" if best else "t2"}" x="{NOTE_X}" y="{y + (0 if best else 4)}" font-size="13"'
               f'{weight}>{s["p_his"]:.3f}</text>')
    if best:
        t = tests["NAME/p"][arm]
        lo_d, hi_d = t["ci90"]
        svg.append(f'<text class="t2" x="{NOTE_X}" y="{y + 16}" font-size="11">+{t["diff"]:.3f} vs name only '
                   f'[{lo_d:+.3f}, {hi_d:+.3f}]</text>')
svg.append(f'<text class="t2" x="20" y="{H - 14}" font-size="11">Right-column intervals are for the paired difference '
           'on the same pairs (90%, resampling works). Sonnet predictor.</text>')
svg.append("</svg>")
(HERE / "figure.svg").write_text("\n".join(svg) + "\n")
print(json.dumps({"arms": summary, "vs_name_p": tests["NAME/p"]}, indent=1))

# The two winning profiles, exactly as the predictor saw them.
s_inf = json.load(open("synthme/S_inf.json"))["artifacts"]
card = json.load(open("e2_climb/confirm_A.json"))["text"]
lines = ["# The two best profiles, verbatim", "",
         "## Contrastive card (e2_v4 arm P4; the climb kept it unchanged)", "", card, "",
         "## Informal-writing persona (synthme arm S_inf)", "", s_inf["persona"], "",
         "Shown to the predictor with these two past choices as exemplars:", ""]
for e in s_inf["exemplars"]:
    chosen = e["a_text"] if e["chosen"] == "a" else e["b_text"]
    other = e["b_text"] if e["chosen"] == "a" else e["a_text"]
    lines += [f"- **Context.** {e['context']}", f"  - Chose: {chosen}", f"  - Over: {other}", ""]
(HERE / "profiles.md").write_text("\n".join(lines))
