"""Build the taste-pipeline diagrams from one source.

Writes docs/pipeline/*.svg (shown on GitHub by docs/pipeline.md), docs/pipeline.md itself, and
docs/pipeline/index.html (the same page, published as a claude.ai artifact). Edit the data
below, never the generated files; tests/test_pipeline_diagram.py fails when they drift.

    python3 scripts/build_pipeline_diagram.py           # rewrite the generated files
    python3 scripts/build_pipeline_diagram.py --check   # exit 1 if any is stale
"""
import argparse
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT_DIR = DOCS / "pipeline"
ARTIFACT_URL = "https://claude.ai/artifact/F2kpYLDpiEtXNb4F9K1FVN"

# ---------------------------------------------------------------- pipeline data
# step: (number, cli stage, title, detail, mono line, status "ran" | "built", [output lines])
PRISM = [
    ("1", "prepare", "Download and clean PRISM", "16,693 choices from 723 users; 12 exact repeats dropped",
     "taste prepare · no model", "ran", ["runs/prefdata/prism.jsonl", "data/prefdata/prism-splits.json"]),
    ("2", "split", "Split by user", "345 development users · 378 final-test users",
     "final-test users can be scored once (--final)", "ran", []),
    ("3", "fidelity", "Fit and predict M0–M7", "each user: fit on their history, predict their test choices",
     "taste fidelity · codex-cli (--backend, --model)", "built",
     ["runs/fidelity/dev/predictions.jsonl", "runs/fidelity/dev/report.json"]),
    ("4", "schema", "Search feature schemas (optional)", "development users only",
     "scripts/schema_search.py", "built", []),
    ("5", "E1", "E1: pick the best method", "user-macro accuracy and Brier; must beat M1, CI above 0",
     "on the final-test users, once", "built", ["selected method + config", "posted to the team"]),
]
PRISM_TERMINAL = ("Output: the selected method", "no winner yet; Track P and Track S take it by hand",
                  "(trackp e2 and fit; track_eval --selected)")

TRACK_P = [
    ("1", "init", "Register the person", "records their consent and adds the track",
     "trackp init · no model", "built", ["CONSENT.md", "data/researchers/tracks.json"]),
    ("2", "seed-pairs", "Make 50 seed pairs", "two library interventions on the same scenario",
     "trackp seed-pairs · --llm-ideas adds paid ones", "built", ["seed_pairs.jsonl"]),
    ("3", "record", "Collect their choices", "seed pairs, plus D1–D6 decisions from loop runs",
     "trackp pending + record, or answer / label", "built", ["seed_choices.jsonl", "labels.jsonl"]),
    ("4", "recheck", "Re-ask 20% after 3 days", "options reversed; the agreement rate is the noise ceiling",
     "trackp recheck", "built", ["recheck.jsonl"]),
    ("5", "split", "Hold out a test set", "20% of seed pairs + labels from runs after --label-cutoff",
     "trackp split · rest is history and val", "built", []),
    ("6", "e2", "E2: beat M1 on held-out choices", "selected method vs M0, M1 and the noise ceiling",
     "trackp e2 · offline, claude-haiku-5-5", "built", ["results/e2/P_<slug>.json"]),
    ("7", "fit", "Fit the user model", "selected method on history + val; held-out never used",
     "trackp fit --method --config --backend --model", "built", ["usermodel.json", "history.jsonl"]),
]

TRACK_S = [
    ("1", "harvest", "Harvest his dated work", "127 kept of 1,757 found, 2020–2026; authorship checked",
     "Exa only, no LLM · about $1.70", "ran", ["corpus/research__*.txt", "harvest_manifest.jsonl"]),
    ("2", "extract", "Extract his decisions", "Exa structured summary: D1–D6 decisions with quotes",
     "Exa only, no LLM", "built", ["extraction/exa.jsonl"]),
    ("3", "check", "Check each decision", "Claude keeps, fixes or drops; code verifies each quote",
     "claude-cli · claude-sonnet-5-5 · --max-usd", "built",
     ["extraction/decisions.jsonl", "extraction/rejected.jsonl"]),
    ("4", "distract", "Find an alternative per decision", "decisions before T see only material from before T",
     "claude-sonnet-5-5, plus Exa", "built", ["extraction/distractors.jsonl"]),
    ("5", "pairs", "Build pairs, split at date T", "anonymised; T not chosen yet (needs ≥ 40 held-out pairs)",
     "no model", "built", ["history_timesplit.jsonl", "heldout_timesplit.jsonl"]),
    ("6", "gate", "Gate: are the pairs guessable?", "blind judge; regenerate if over 75% guessable",
     "track_eval gate · claude-opus-5-5", "built", ["gate_timesplit.jsonl"]),
    ("7", "select", "Pick a method on history", "m2–m7; stands in while E1 has no winner",
     "track_eval select · claude-sonnet-5-5", "built", []),
    ("8", "e2", "E2: beat both M1 arms", "a pair counts only if both option orders are right",
     "track_eval e2 · + m0_named contamination probe", "built", ["results/track_s/E2_<slug>.json"]),
    ("9", "final", "Fit the user model", "selected method on history + held-out",
     "track_eval final", "built", ["usermodel.json"]),
]

# Hand-placed: the loop has branches a step list can't show.
DOWNSTREAM = """
<rect class="lane alt" x="0" y="0" width="960" height="110"/>
<rect class="lane" x="0" y="110" width="960" height="216"/>
<rect class="lane alt" x="0" y="326" width="960" height="364"/>
<line class="divider" x1="0" y1="110" x2="960" y2="110"/>
<line class="divider" x1="0" y1="326" x2="960" y2="326"/>

<text class="ll" x="16" y="38">USER MODEL</text><text class="lw" x="16" y="54">Track P or S</text>
<text class="ll" x="16" y="142">RESEARCH LOOP</text><text class="lw" x="16" y="158">WS D</text>
<text class="ll" x="16" y="358">MEASUREMENT</text><text class="lw" x="16" y="374">WS C1 · WS C2</text>

<rect class="store" x="170" y="24" width="200" height="56" rx="6"/>
<text class="t" x="182" y="47">past.dev</text>
<text class="d" x="182" y="65">shared memory across agents</text>

<rect class="store" x="430" y="24" width="220" height="56" rx="6"/>
<text class="tm" x="442" y="47">usermodel.json</text>
<text class="d" x="442" y="65">one per track</text>

<rect class="box" x="710" y="24" width="230" height="56" rx="6"/>
<text class="t" x="722" y="47">Taste-Bench · E7</text>
<text class="d" x="722" y="65">picks the step that worked? 112 forks</text>

<path class="e" d="M428,52 H372" marker-start="url(#ad)" marker-end="url(#ad)"/>
<text class="el" x="400" y="44" text-anchor="middle">push / pull</text>
<path class="e" d="M650,52 H708" marker-end="url(#ad)"/>
<text class="el" x="679" y="44" text-anchor="middle">tested</text>

<path class="e" d="M500,80 V98 H280 V122" marker-end="url(#ad)"/>
<text class="el" x="390" y="93" text-anchor="middle">consulted at D1–D6</text>

<rect class="box" x="170" y="124" width="220" height="84" rx="6"/>
<text class="t" x="182" y="146">TasteAdvisor</text>
<text class="d" x="182" y="164">asked at decision points D1–D6</text>
<text class="d" x="182" y="181">followed if confidence ≥ 0.6</text>
<text class="m" x="182" y="198">model: user model, on judge</text>

<rect class="box" x="430" y="124" width="220" height="84" rx="6"/>
<text class="t" x="442" y="146">Proposer</text>
<text class="d" x="442" y="164">writes and edits environments</text>
<text class="d" x="442" y="181">reads A1–A3 scores next round</text>
<text class="m" x="442" y="198">model: sonnet (generator)</text>

<rect class="box" x="710" y="124" width="230" height="84" rx="6"/>
<text class="t" x="722" y="146">Loop arms</text>
<text class="d" x="722" y="164">R0 no taste · R1-P · R1-S</text>
<text class="d" x="722" y="181">-prompt: raw history in prompt</text>
<text class="d" x="722" y="198">R1-bad: contrarian taste</text>

<path class="e" d="M390,166 H428" marker-end="url(#ad)"/>
<text class="el" x="410" y="158" text-anchor="middle">advice</text>
<path class="e" d="M710,166 H652" marker-end="url(#ad)"/>
<text class="el" x="681" y="158" text-anchor="middle">taste</text>

<rect class="store" x="170" y="240" width="220" height="64" rx="6"/>
<text class="t" x="182" y="262">Loop memory</text>
<text class="d" x="182" y="280">OUTCOME and DECISION facts</text>
<text class="d" x="182" y="297">local file, or past.dev</text>
<path class="e" d="M470,208 V272 H392" marker-end="url(#ad)"/>
<text class="el" x="478" y="246">writes</text>

<rect class="box plan" x="710" y="240" width="230" height="64" rx="6"/>
<text class="t" x="722" y="262">External-agent arm</text>
<text class="d" x="722" y="280">same task, outside research agent</text>
<path class="e plan" d="M710,272 H610 V210" marker-end="url(#ad)"/>
<text class="el" x="660" y="264" text-anchor="middle">same task</text>

<path class="e" d="M540,208 V350" marker-end="url(#ad)"/>
<text class="el" x="548" y="316">environments</text>

<rect class="box" x="170" y="362" width="220" height="84" rx="6"/>
<text class="t" x="182" y="384">EvalAwareBench</text>
<text class="d" x="182" y="402">200 items: 128 dev, 72 held-out</text>
<text class="d" x="182" y="419">gate: AUROC ≥ 0.85, κ ≥ 0.6</text>
<text class="d" x="182" y="436">gate not run yet</text>
<path class="e" d="M390,404 H428" marker-end="url(#ad)"/>
<text class="el" x="410" y="396" text-anchor="middle">tasks</text>

<rect class="box" x="430" y="352" width="220" height="106" rx="6"/>
<text class="t" x="442" y="374">Target model</text>
<text class="d" x="442" y="392">the model under study</text>
<text class="m" x="442" y="409">model: haiku</text>
<text class="d" x="442" y="426">held-out target in final mode</text>

<rect class="box plan" x="710" y="352" width="230" height="48" rx="6"/>
<text class="t" x="722" y="372">Petri audits</text>
<text class="d" x="722" y="390">simulated or Modal sandbox tools</text>
<path class="e plan" d="M710,376 H652" marker-end="url(#ad)"/>

<rect class="box plan" x="710" y="410" width="230" height="48" rx="6"/>
<text class="t" x="722" y="430">Open-weight target</text>
<text class="d" x="722" y="448">reasoning model on Modal</text>
<path class="e plan" d="M710,434 H652" marker-end="url(#ad)"/>

<path class="e" d="M480,458 V480 H280 V498" marker-end="url(#ad)"/>
<text class="el" x="380" y="474" text-anchor="middle">transcripts</text>
<path class="e" d="M590,458 V498" marker-end="url(#ad)"/>
<text class="el" x="598" y="484">answers</text>

<rect class="box" x="170" y="500" width="220" height="84" rx="6"/>
<text class="t" x="182" y="522">Judge J1</text>
<text class="d" x="182" y="540">A1: awareness in reasoning</text>
<text class="d" x="182" y="557">+ validity · A3: synthetic vs real</text>
<text class="m" x="182" y="574">model: sonnet (judge)</text>

<rect class="box" x="430" y="500" width="220" height="84" rx="6"/>
<text class="t" x="442" y="522">A2 probes</text>
<text class="d" x="442" y="540">target asked for P(eval) after</text>
<text class="d" x="442" y="557">EvalDetectBench probes</text>
<text class="d" x="442" y="574">held-out judges too, final mode</text>

<rect class="box" x="170" y="616" width="220" height="52" rx="6"/>
<text class="t" x="182" y="638">Held-out judge J2</text>
<text class="d" x="182" y="656">final mode only</text>
<path class="e plan" d="M280,616 V586" marker-end="url(#ad)"/>
<text class="el" x="288" y="606">replaces J1 in final mode</text>
"""

# ---------------------------------------------------------------- page text
# Prose uses `code` spans; they become <code> in HTML and stay as-is in Markdown.
TITLE = "Taste Pipeline"
LEDE = ("The project builds synthetic test environments that a target model should not recognise as "
        "evaluations, using a research loop steered by a model of one researcher's taste (PLAN.md §0). "
        "Three separate pipelines feed it. PRISM picks the modelling method. Track P and Track S each fit "
        "that method to one person and produce a `usermodel.json`. The last figure shows where those files go.")

COMPARE = (["", "PRISM", "Track P", "Track S"], [
    ["Whose taste", "723 crowd users", "One team member, not chosen yet", "Marius Hobbhahn"],
    ["Where choices come from", "Released chatbot preference data",
     "They answer pairs and label loop decisions", "Decisions extracted from his dated writing"],
    ["Held-out test", "Final-test users, scored once", "20% of seed pairs + labels after a cutoff",
     "Decisions after date T"],
    ["Experiment", "E1: which method", "E2 vs M1 and the noise ceiling", "E2 vs two M1 arms, order-paired"],
    ["Output", "Selected method", "`usermodel.json`", "`usermodel.json`"],
    ["Furthest step run", "1–2 (data ready)", "None", "1 (harvest)"],
])

# section: (anchor, heading, intro, figure key, caption)
SECTIONS = [
    ("prism", "PRISM: pick the method",
     "Choices from many users decide which of the eight user-model methods to use. Owned by WS A. "
     "Commands run as `python3 -m autoresearch.taste <stage>`.",
     "prism",
     "E1 has no result yet, so no method has been selected. Nothing passes the method on automatically: "
     "Track P and Track S each take it by hand."),
    ("track-p", "Track P: a team member",
     "The person answers choices directly. Owned by WS B. Commands run as "
     "`python3 -m autoresearch.taste.trackp <stage>`; files land in `data/researchers/<slug>/`. "
     "The runbook is `docs/trackp-runbook.md`.",
     "track-p",
     "Every step is built and none has run, because the person hasn't been chosen (it won't be Ethan). "
     "Only this track has a human answering questions and a recheck that measures their own noise."),
    ("track-s", "Track S: Marius Hobbhahn",
     "His taste is inferred from what he published, and the model is tested on decisions he made after "
     "date T. Owned by WS B. Steps 1–5 run as `python3 -m autoresearch.taste.timesplit <stage>`, steps "
     "6–9 as `track_eval <stage>`. Files land in `data/researchers/marius_hobbhahn/`.",
     "track-s",
     "The harvest has run; everything after it is built and waits on date T. Only this track has the Exa "
     "harvest, the quote check, the distractor gate, and the contamination probe (`m0_named`: the model "
     "is told his name and gets no history)."),
    ("downstream", "After the user model",
     "Both tracks produce the same file, so everything from here on is shared.",
     "downstream",
     "Each loop arm gives the proposer a different kind of taste. In the R1 arms the TasteAdvisor asks the "
     "user model at decision points D1–D6. The proposer's environments, alongside EvalAwareBench tasks, go "
     "to the target model. Judge J1 reads the target's reasoning (A1, plus validity) and tells synthetic "
     "from real (A3). Probe questions give A2."),
]

RESULTS_INTRO = ("PLAN §0 reports four results and never merges them into one score. Experiments are "
                 "defined in PLAN §9; E6, a stretch goal, is left out.")
RESULTS = (["Result", "Experiments", "Pipeline"], [
    ["1. Preference fidelity", "E1 (methods on PRISM), E2 (each track's held-out choices)",
     "PRISM, Track P, Track S"],
    ["2. Research judgment", "E4b (blinded ratings of the loop's D1–D6 decisions), E7 (Taste-Bench)",
     "After the user model"],
    ["3. Downstream outcome", "E3a (single scenario), E3b (Petri), E4 (taste vs no taste)", "After the user model"],
    ["4. Efficiency", "E5 (cost and wall time per validated finding)", "After the user model"],
])

TERMS = (["Term", "Meaning"], [
    ["M0–M7", "The user-model methods: M0 no history, M1 raw history, M2 SynthesizeMe persona, M3 ICAI "
     "principles, M4 Bradley–Terry on 7 LLM-scored features, M5 = M2 + M3 + examples, M6 = M5 pruned, "
     "M7 = M6 calibrated."],
    ["Date T", "Track S's time split: the model is built from his work before T and tested on decisions after it."],
    ["D1–D6", "The loop's decision points: what to test next, what evidence to collect, accept or reject a "
     "result, pursue or drop a direction, how to read a surprising result, what to claim."],
    ["Noise ceiling", "How often Track P's person gives the same answer when asked again; no model can be "
     "expected to beat it."],
    ["TasteAdvisor", "Asks the user model which option the researcher would pick. Below confidence 0.6 the "
     "loop decides on the evidence alone."],
    ["A1 · A2 · A3", "A1: a judge marks whether the target's reasoning says it is being tested. A2: the "
     "target is asked afterwards and gives P(eval). A3: a judge picks the synthetic message out of a "
     "synthetic/real pair."],
    ["Final mode", "`--mode final`: swaps in the held-out target, judges and benchmark split, used only for "
     "reported numbers."],
    ["past.dev", "The shared memory service used across agents and runs; without `PAST_API_KEY` a local "
     "file stands in."],
])

# ---------------------------------------------------------------- styles
TOKENS = """
:root {
  --bg: #f7f8fa; --fg: #1a1f29; --muted: #5b6474; --line: #d5dae3; --lane: #eef1f5; --box: #ffffff;
  --store: #e3eefa; --store-line: #4a7ab5; --edge: #4b5363; --accent: #0f7d6e;
  --ok-bg: #d8f0e4; --ok-ink: #145a37; --built-bg: #f6e7c8; --built-ink: #6b4a0e;
  --sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #12151b; --fg: #e4e8ef; --muted: #98a1b0; --line: #2c333f; --lane: #181c24; --box: #1d222b;
    --store: #172a40; --store-line: #6c9bd4; --edge: #a3acba; --accent: #3cc2ad;
    --ok-bg: #173a29; --ok-ink: #8fdcb2; --built-bg: #3d3018; --built-ink: #f0cd85; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #12151b; --fg: #e4e8ef; --muted: #98a1b0; --line: #2c333f; --lane: #181c24; --box: #1d222b;
  --store: #172a40; --store-line: #6c9bd4; --edge: #a3acba; --accent: #3cc2ad;
  --ok-bg: #173a29; --ok-ink: #8fdcb2; --built-bg: #3d3018; --built-ink: #f0cd85; color-scheme: dark;
}"""

SVG_CSS = """
svg .bg { fill: var(--box); }
svg .lane { fill: var(--box); }
svg .lane.alt { fill: var(--lane); }
svg .divider { stroke: var(--line); stroke-width: 1; }
svg .ll { fill: var(--fg); font: 600 11px var(--sans); letter-spacing: 0.08em; }
svg .lw { fill: var(--muted); font: 400 11px var(--sans); }
svg .num { fill: var(--accent); font: 600 15px var(--sans); }
svg .stg { fill: var(--fg); font: 500 12px var(--mono); }
svg .box { fill: var(--box); stroke: var(--edge); stroke-width: 1.4; }
svg .box.plan { stroke-dasharray: 6 4; }
svg .store { fill: var(--store); stroke: var(--store-line); stroke-width: 1.4; }
svg .t { fill: var(--fg); font: 600 13px var(--sans); }
svg .tm { fill: var(--fg); font: 500 12.5px var(--mono); }
svg .d { fill: var(--muted); font: 400 11.5px var(--sans); }
svg .m { fill: var(--muted); font: 400 11px var(--mono); }
svg .m.out { fill: var(--fg); }
svg .chip-ok { fill: var(--ok-bg); }
svg .chip-ok-t { fill: var(--ok-ink); font: 600 11px var(--sans); }
svg .chip-built { fill: var(--built-bg); }
svg .chip-built-t { fill: var(--built-ink); font: 600 11px var(--sans); }
svg .e { fill: none; stroke: var(--edge); stroke-width: 1.4; }
svg .e.plan { stroke-dasharray: 5 4; }
svg .ah { fill: var(--edge); }
svg .el { fill: var(--muted); font: italic 400 11px var(--sans); }"""

PAGE_CSS = """
body {
  background: var(--bg); color: var(--fg); font-family: var(--sans); font-size: 15px; line-height: 1.6;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 40px 64px;
}
main { max-width: 1000px; margin: 0 auto; display: grid; gap: 48px; }
h1 { font-size: 30px; font-weight: 600; margin: 0 0 8px; letter-spacing: -0.01em; text-wrap: balance; }
h2 { font-size: 20px; font-weight: 600; margin: 0 0 6px; text-wrap: balance; }
p { margin: 0; max-width: 68ch; }
code { font-family: var(--mono); font-size: 0.88em; }
a { color: var(--accent); }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.lede { color: var(--muted); }
.intro { margin-bottom: 14px; color: var(--muted); }
nav.jump { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
nav.jump a { text-decoration: none; font-size: 13.5px; font-weight: 500; padding: 5px 12px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--box); color: var(--fg); }
nav.jump a:hover { border-color: var(--accent); }
.legend { display: flex; flex-wrap: wrap; gap: 10px 22px; margin-top: 16px; font-size: 13px; color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 8px; }
.sw { width: 26px; height: 16px; border-radius: 4px; border: 1.5px solid var(--edge); background: var(--box); }
.sw.plan { border-style: dashed; }
.sw.store { background: var(--store); border-color: var(--store-line); }
.pill { font-size: 11px; font-weight: 600; padding: 1px 9px; border-radius: 999px; }
.pill.ok { background: var(--ok-bg); color: var(--ok-ink); }
.pill.built { background: var(--built-bg); color: var(--built-ink); }
figure { margin: 0; }
.frame { overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--box); }
.frame svg { display: block; width: 100%; min-width: 780px; height: auto; }
figcaption { margin-top: 12px; font-size: 14px; color: var(--muted); max-width: 72ch; }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--box); }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; min-width: 640px; }
th, td { text-align: left; vertical-align: top; padding: 10px 14px; border-bottom: 1px solid var(--line); }
th { font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--muted); background: var(--lane); }
tr:last-child td { border-bottom: 0; }
td:first-child { font-weight: 500; }
th:not(:last-child), td:not(:last-child) { border-right: 1px solid var(--line); }"""

# ---------------------------------------------------------------- drawing
PITCH, BOX_H, TOP = 100, 72, 20
CHIP = {"ran": "chip-ok", "built": "chip-built"}


def _t(cls, x, y, s, anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    return f'<text class="{cls}" x="{x}" y="{y}"{a}>{escape(s)}</text>'


def _marker(mid):
    return (f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path class="ah" d="M0,0 L10,5 L0,10 z"/></marker></defs>')


def pipeline_body(steps, mid, terminal=None):
    """Return (svg body, height) for a numbered top-to-bottom step list."""
    rows = len(steps) + (1 if terminal else 0)
    h = TOP + rows * PITCH - (PITCH - BOX_H) + TOP
    p = [f'<rect class="lane alt" x="0" y="0" width="150" height="{h}"/>',
         f'<rect class="lane alt" x="610" y="0" width="350" height="{h}"/>']
    for i, (num, stage, title, detail, mono, status, outs) in enumerate(steps):
        y = TOP + i * PITCH
        chip = CHIP[status]
        p += [_t("num", 20, y + 27, num), _t("stg", 44, y + 27, stage),
              f'<rect class="box" x="170" y="{y}" width="400" height="{BOX_H}" rx="6"/>',
              _t("t", 184, y + 26, title), _t("d", 184, y + 45, detail), _t("m", 184, y + 62, mono),
              f'<rect class="{chip}" x="500" y="{y + 11}" width="58" height="20" rx="10"/>',
              _t(chip + "-t", 529, y + 25, status, "middle")]
        if outs:
            p += [f'<path class="e" d="M570,{y + 36} H638" marker-end="url(#{mid})"/>',
                  f'<rect class="store" x="640" y="{y + 12}" width="300" height="48" rx="6"/>']
            if len(outs) == 1:
                p.append(_t("m out", 654, y + 40, outs[0]))
            else:
                p += [_t("m out", 654, y + 32, outs[0]), _t("m out", 654, y + 50, outs[1])]
        if i < rows - 1:
            p.append(f'<path class="e" d="M370,{y + BOX_H} V{y + PITCH - 2}" marker-end="url(#{mid})"/>')
    if terminal:
        y = TOP + len(steps) * PITCH
        p += [f'<rect class="store" x="170" y="{y}" width="400" height="{BOX_H}" rx="6"/>',
              _t("t", 184, y + 28, terminal[0]), _t("d", 184, y + 47, terminal[1]),
              _t("d", 184, y + 64, terminal[2])]
    return "\n".join(p), h


FIGURES = {
    # key: (marker id, aria label, body, height)
    "prism": ("ap", "PRISM pipeline: download and split 723 users, fit methods M0 to M7, and pick the best in E1.",
              *pipeline_body(PRISM, "ap", PRISM_TERMINAL)),
    "track-p": ("aq", "Track P pipeline: register, make seed pairs, collect and recheck choices, hold out a test "
                "set, run E2, fit usermodel.json.", *pipeline_body(TRACK_P, "aq")),
    "track-s": ("as", "Track S pipeline: harvest dated work with Exa, extract and check decisions, find "
                "alternatives, split at date T, gate, select, run E2, fit usermodel.json.",
                *pipeline_body(TRACK_S, "as")),
    "downstream": ("ad", "Using the user model: it syncs to past.dev and is tested on Taste-Bench; the "
                   "TasteAdvisor consults it at D1 to D6 and advises the proposer; the proposer's environments "
                   "go to the target model; judge J1 scores transcripts for A1 and A3, and probes give A2.",
                   DOWNSTREAM, 690),
}


def svg(key, standalone):
    mid, label, body, h = FIGURES[key]
    if standalone:  # GitHub shows it through <img>, so it carries its own styles and background
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {h}" width="960" height="{h}" '
                f'role="img" aria-label="{escape(label)}">\n<style>{TOKENS}{SVG_CSS}\n</style>\n'
                f'{_marker(mid)}\n<rect class="bg" x="0" y="0" width="960" height="{h}"/>\n{body}\n</svg>\n')
    return f'<svg viewBox="0 0 960 {h}" role="img" aria-label="{escape(label)}">\n{_marker(mid)}\n{body}\n</svg>'


# ---------------------------------------------------------------- pages
def _html(s):
    return re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", escape(s, quote=False))


def _html_table(table):
    head, rows = table
    th = "".join(f"<th>{_html(c)}</th>" for c in head)
    body = "\n".join("<tr>" + "".join(f"<td>{_html(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="table-wrap"><table>\n<thead><tr>{th}</tr></thead>\n<tbody>\n{body}\n</tbody>\n</table></div>'


def _md_table(table):
    head, rows = table
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def build_html():
    nav = "\n".join(f'<a href="#{a}">{_html(h)}</a>' for a, h, *_ in SECTIONS)
    sections = "\n".join(
        f'<section id="{a}">\n<h2>{_html(h)}</h2>\n<p class="intro">{_html(intro)}</p>\n'
        f'<figure><div class="frame">\n{svg(key, False)}\n</div>\n<figcaption>{_html(cap)}</figcaption></figure>\n'
        f'</section>' for a, h, intro, key, cap in SECTIONS)
    return f"""<title>{TITLE}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<!-- Generated by scripts/build_pipeline_diagram.py; edit that, not this file. -->
<style>{TOKENS}{PAGE_CSS}{SVG_CSS}
</style>
<main>
<header>
<h1>{TITLE}</h1>
<p class="lede">{_html(LEDE)}</p>
<nav class="jump" aria-label="Pipelines">
{nav}
</nav>
<div class="legend" aria-label="Legend">
<span><b class="pill ok">ran</b>Built and has run on real data</span>
<span><b class="pill built">built</b>Built, not run yet</span>
<span><i class="sw store"></i>File it writes</span>
<span><i class="sw plan"></i>Planned, not built</span>
</div>
</header>
<section>
<h2>How the three differ</h2>
{_html_table(COMPARE)}
</section>
{sections}
<section>
<h2>Where each result comes from</h2>
<p class="intro">{_html(RESULTS_INTRO)}</p>
{_html_table(RESULTS)}
</section>
<section>
<h2>Terms</h2>
{_html_table(TERMS)}
</section>
</main>
"""


def build_md():
    parts = [
        "# Taste pipeline",
        "",
        "<!-- Generated by scripts/build_pipeline_diagram.py; edit that, not this file. -->",
        "",
        LEDE,
        "",
        f"Interactive version: [claude.ai artifact]({ARTIFACT_URL}). In each figure a green `ran` tag means the "
        "step has run on real data, an amber `built` tag means it is built but not run yet, blue boxes are "
        "files the step writes, and dashed boxes are planned and not built.",
        "",
        "## How the three differ",
        "",
        _md_table(COMPARE),
    ]
    for _anchor, heading, intro, key, cap in SECTIONS:
        parts += ["", f"## {heading}", "", intro, "", f"![{FIGURES[key][1]}](pipeline/{key}.svg)", "", cap]
    parts += ["", "## Where each result comes from", "", RESULTS_INTRO, "", _md_table(RESULTS),
              "", "## Terms", "", _md_table(TERMS), "",
              "## Updating this page", "",
              "Edit the data in `scripts/build_pipeline_diagram.py`, then run it. It rewrites this file, the "
              "SVGs in `docs/pipeline/` and `docs/pipeline/index.html`; commit all of them. "
              "`tests/test_pipeline_diagram.py` fails while any of them is stale. Then republish "
              "`docs/pipeline/index.html` to the artifact link above so it matches.", ""]
    return "\n".join(parts)


def outputs():
    """Map each generated path to its content."""
    files = {OUT_DIR / f"{key}.svg": svg(key, True) for key in FIGURES}
    files[OUT_DIR / "index.html"] = build_html()
    files[DOCS / "pipeline.md"] = build_md()
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if a generated file is stale")
    args = ap.parse_args()
    stale = [p for p, text in outputs().items() if not p.exists() or p.read_text() != text]
    if args.check:
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)}")
        sys.exit(1 if stale else 0)
    OUT_DIR.mkdir(exist_ok=True)
    for p, text in outputs().items():
        p.write_text(text)
    print(f"wrote {len(outputs())} files ({len(stale)} changed)")


if __name__ == "__main__":
    main()
