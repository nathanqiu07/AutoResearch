# Source-to-decision trail and GPU-time market bids

Two offline tools for the sponsor story (PLAN §8, §10). Neither makes network, model or Modal calls.

## 1. Source-to-decision trail (Exa + past.dev)

`autoresearch/integrations/trail.py` rebuilds, for every critic veto and every credence update from a web
fact-check in a run, the chain

```
Exa source (URL, publish date, used_for)
  -> EVIDENCE fact (stance, confidence, URLs)              shared memory
  -> veto / credence change (iteration, change, assumption key)
  -> what ran instead: history entry, decision record, OUTCOME fact
     (and the vetoed change's outcomes elsewhere in this run and in other runs)
```

```bash
# a directory is searched recursively for run reports, shared-memory JSONL, decision logs, assumptions.json
python3 -m autoresearch.integrations.trail RUN_DIR
python3 -m autoresearch.integrations.trail RUN_DIR --memory runs/shared_memory.jsonl \
    --decisions runs/memory/decisions.jsonl --html trail.html --md trail.md
python3 -m autoresearch.integrations.trail RUN_DIR --json > trail.json

# the demo, with the trail as an optional fifth moment (committed results only)
python3 scripts/demo.py --trail [--paths results/...] [--strict]
```

The v1 loop (`autoresearch run`) writes its shared memory to `--shared-path` (default
`runs/shared_memory.jsonl`) and its decision log to `<--memory>/decisions.jsonl`. When those files live
outside RUN_DIR, pass them with `--memory` and `--decisions`. The v2 loop (`autoresearch research`)
writes `<memory>/shared.jsonl`, and its report already contains its decision records.

The HTML page is static and self-contained: inline CSS, no scripts, no external assets.

**Joins.** Every link uses only keys the run recorded:

| Link | Join key | Notes |
|---|---|---|
| Source to EVIDENCE | `Source.detail == EVIDENCE.change`, URL in `EVIDENCE.urls`, `used_for == fact_check` | A cited URL with no Source record shows as MISSING |
| EVIDENCE iteration | Write order in a local JSONL: each v1 iteration writes its EVIDENCE before its one OUTCOME | Not available from past.dev recall, so it shows as MISSING |
| EVIDENCE to veto | `web_refuted` detail `"<change> refuted by <urls>"`; the fact with `stance=refute` and exactly those URLs is marked `cited_by_veto` | The other EVIDENCE facts for the change are listed with stance counts |
| Credence change | Assumption `<task>:<change>`, weight `0.5 x confidence` (the rule in `loop.Researcher._critic_allows`) | The final credence comes from `assumptions.json` if present, labelled as covering the whole run |
| What ran instead | v1 decision record and history entry at the veto's iteration | `veto_overridden` means everything was gated and the loop fell back to the vetoed change |
| OUTCOME | `(run, change, round(delta, 4))` against the history entry | |
| v2 Exa idea | `web_ideas[].source_url` against `sources[].url`; bids by `add:<idea id>`; findings by move; OUTCOME by `(run, category, delta, status)`; decisions by design text | |

The v2 loop has no fact-check step. It writes no EVIDENCE, so no web-based veto exists in v2 runs. The
trail reports this (`v2.fact_check`) and instead traces each `exa`-origin idea to its bids, the critic's
bids against it, its findings, OUTCOME facts, D1/D3/D5 records and the final design. The only v2 veto,
`gated_refuted_category`, comes from memory and is traced the same way.

**Fields the loops do not record.** Each trail lists these links as missing, and the page ends with this
table. Adding the fields would close the links. Those files are owned by other workstreams, so the
changes are not made here:

| Field | Where it would go | Effect today |
|---|---|---|
| `source.iter`, `source.fact_ref` | `exa.Source` (iteration, id of the EVIDENCE fact it fed) | Sources join EVIDENCE on (change, URL) only, so repeated checks of one change cannot be told apart |
| `evidence.iter` | EVIDENCE fact in `loop._critic_allows` | Recovered from write order only for a local JSONL |
| `veto.evidence_refs` | `DriftEvent("web_refuted")` | The veto keeps only the first refuting fact's URLs, not the facts it weighed or their counts |
| `veto.refute_confidence` | v1 `RunReport` (no config) | Which refutations counted toward the veto cannot be checked |
| `credence.before_after` | `ResearchMemory.update` | Only the final alpha/beta are saved |
| `outcome.iter` | v1 OUTCOME fact | Joined to history on delta |
| `decision.vetoed` | v1 `record_decision` | Ranked options do not say which ones were vetoed |
| `web_ideas.iter`, `source.query` | v2 `_discover` | An idea joins its source by URL only |
| `v2.outcome_move` | v2 OUTCOME fact (`change=<category>`) | Joined to the finding on (category, delta, status) |

**Committed results today.** No committed run under `results/` records a web veto or any Exa source:
every report's `sources` is empty or absent. So `demo.py --trail` reports the
fifth moment as MISSING. A live run with `EXA_API_KEY` and shared memory on is needed to fill it.

## 2. Market bids in GPU time (Modal + past.dev)

`autoresearch/research/market.py` adds a GPU-seconds resource for runs on the self-hosted target
(`llm.OpenAICompatLLM`, for example vLLM on Modal). Without a GPU budget, the wallets file, ledger
entries and BID/SETTLE facts are exactly as before.

```python
from autoresearch.research.market import Market, Wallets, GpuUsage, audit_ledger, ledger_facts

market = Market(Wallets("runs/research_memory/wallets.json", gpu_initial=3600.0),   # GPU-s per agent
                shared=shared, run_id=run_id)                    # usd_per_hour defaults to OPENAI_COMPAT_USD_PER_HOUR
usage = GpuUsage(budget)                                         # reads Budget.gpu_seconds (charged by llm.GpuMeter)

market.bid("scout", "add:abc", 0.6, gpu_s=120)                   # ask for 120 GPU-s; stake is credits as before
with usage.measure("add:abc"):
    ...                                                          # measure the candidate on the self-hosted target
market.settle({"add:abc": validated}, gpu_seconds=usage.pop(["add:abc"]))
```

* **Bid.** `gpu_s` is a request. It is refused (`bid_refused`, `reason=gpu_s`) when it exceeds the
  agent's GPU balance minus its other open requests. A bid against a candidate (the critic) cannot ask
  for GPU time.
* **Settle.** The candidate's **measured** GPU-seconds are split among its GPU bids in proportion to the
  amounts requested, and charged to those bidders. The bid amount itself is not charged. A settlement
  that includes GPU bids raises `ValueError` without a measurement, and pays nothing. The balance stops
  at zero, and any overrun is recorded as `gpu_s_unpaid`. Withdrawn bids are released without charge.
  The credit payoff is the log score, unchanged.
* **Facts.** `BID ... resource=gpu_s gpu_s_bid=<requested> gpu_balance=<at bid>` and
  `SETTLE ... resource=gpu_s gpu_s=<measured share> gpu_s_bid gpu_s_measured=<candidate total> gpu_charged gpu_balance [usd_equiv]`.
* **One currency.** `usd_per_gpu_hour()`, `gpu_s_to_usd()` and `usd_to_gpu_s()` convert at
  OPENAI_COMPAT_USD_PER_HOUR (or an explicit `usd_per_hour`). `Market.cost_usd(candidate, usd)` adds the
  largest GPU request to the API cost and returns None when no rate is set. Pass it as
  `order(..., costs=...)` to rank candidates by consensus x stake / $. `report()["gpu"]` gives the
  measured total and its dollar equivalent. A dollar-only market never reads the rate.
* **Measurement.** It is a lower bound, as with `GpuMeter`: idle time before scale-to-zero and cold
  starts are not seen. `GpuUsage.measure` blocks overlap and raises on nested calls. Anything else that
  charges `Budget.gpu_seconds` during the measurement is attributed to the candidate, for example a
  self-hosted judge, which is also GPU spend for that run.

**Ledger audit.** This replays BID/SETTLE facts and checks each agent's balance and track record:

```bash
python3 -m autoresearch.research.market audit runs/research_memory/shared.jsonl \
    --wallets runs/research_memory/wallets.json [--run RUN] [--carried-over] [--gpu-initial 3600]
```

```python
facts, ordered = ledger_facts("runs/research_memory/shared.jsonl")   # or a SharedMemory object
rep = audit_ledger(facts, ordered=ordered, gpu_initial=3600.0, wallets=market.wallets.summary())
rep["ok"], rep["agents"]["scout"], rep["problems"]
```

The checks are:

* every SETTLE has an earlier BID (same run, agent and candidate);
* the payoff equals `stake x ln(q/0.5)`, clipped at zero;
* the balance follows from the previous one;
* a GPU request fits the GPU balance;
* the measured shares of a settlement add up to its measured total;
* the GPU balance falls by exactly what was charged;
* the final balances and settled counts match `wallets.json`.

For wallets carried over from earlier runs, use `--carried-over` (`initial=None`), which takes each
agent's first balance as given. A local JSONL is read in file order, which is write order. past.dev
`recall` order is not, so only the per-fact checks apply there (`ordered=False`). Withdrawals write no
fact, so a BID with no SETTLE is not counted as an error.

**Config wiring.** There is no CLI flag yet. `grid.py` passes pre-registration options through as
`research` CLI flags, and `cli.py` builds `Market(Wallets(...))`. GPU bidding needs these changes, which
belong to the CLI/loop owners and are not made here:

1. `cli.py research`: add `--gpu-budget-s`, giving `Wallets(..., gpu_initial=...)`. After that a
   pre-registration can set `"gpu_budget_s"` through the existing option mapping in `grid.py`.
2. `research/loop.py`: when the dev target is `OpenAICompatLLM`, place bids with `gpu_s=`, for example
   from each agent's expected samples x seconds per sample. Wrap each candidate's `_measure` in
   `GpuUsage.measure(move)`, and pass `usage.pop(...)` to `market.settle(..., gpu_seconds=...)` in `_settle`.

## Tests

```bash
python3 -m unittest tests.test_trail tests.test_market tests.test_demo
python3 -m unittest discover -s tests -t .
```

`tests/test_trail.py` runs the real v1 loop (with a stand-in fact-checking scout and a local shared
memory) and the real v2 loop (with an Exa-origin idea), then checks each link of the trail, the
missing-field reporting, the HTML and the demo's fifth moment. The GPU and audit tests in
`tests/test_market.py` use a fake-clock `GpuMeter`, so they measure no real GPU time.
