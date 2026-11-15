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

**Joins.** Every link uses only keys the run recorded. Runs written by the current loops record exact link
fields; reports and facts from earlier runs lack them, and the trail falls back to the older joins (right
column), listing each fallback as a missing field.

| Link | Exact key (current runs) | Fallback (older runs) |
|---|---|---|
| Source to EVIDENCE | `Source.fact_id == EVIDENCE.id` (and `Source.iteration`, `Source.query`) | `Source.detail == EVIDENCE.change`, URL in `EVIDENCE.urls`, `used_for == fact_check` |
| EVIDENCE iteration | `EVIDENCE.iter` | Write order in a local JSONL (each v1 iteration writes its EVIDENCE before its one OUTCOME); none from past.dev recall |
| EVIDENCE to veto | the `web_refuted` drift event's `evidence` list: every fact the critic weighed (id, run, iter, stance, confidence, URLs, `counted`), with `n_refute`, `n_support`, `refute_confidence` | detail `"<change> refuted by <urls>"`: the refuting fact with exactly those URLs |
| Veto threshold | report `config.loop.refute_confidence` (also `config.scout`, `config.drift`) | none |
| Credence change | report `credence_log` (alpha/beta and credence before and after, per EVIDENCE id) | Assumption `<task>:<change>`, weight `0.5 x confidence` (the loop's rule); final credence from `assumptions.json` |
| What ran instead | v1 decision record (options carry `vetoed`: the veto kind, or null; the record has `fallback`) and history entry at the veto's iteration | the same records without `vetoed` |
| OUTCOME | v1: `(run, change, iter)`; v2: `OUTCOME.finding == finding id` (also `iter`, `move`) | v1 `(run, change, round(delta, 4))`; v2 `(run, category, delta, status)` |
| v2 Exa idea | the `web_ideas` event (`iter`, `query`, new `ideas`, `rediscovered` ids) and `sources[]` with the same `iter` and `query` | `web_ideas[].source_url` against `sources[].url` |

`veto_overridden` means everything was gated and the loop fell back to the vetoed change. In v2, bids join by
`add:<idea id>`, findings by move and decisions by design text, in every run.

The v2 loop has no fact-check step. It writes no EVIDENCE, so no web-based veto exists in v2 runs. The
trail reports this (`v2.fact_check`) and instead traces each `exa`-origin idea to its bids, the critic's
bids against it, its findings, OUTCOME facts, D1/D3/D5 records and the final design. The only v2 veto,
`gated_refuted_category`, comes from memory and is traced the same way. The v2 loop keeps each Exa idea
once per run, by id: a later search that returns it again is logged in that `web_ideas` event's
`rediscovered` list (the trail counts these as `times_discovered`), so one idea never becomes two
candidates with the same design key.

**Fields older runs do not record.** For runs written before the link fields were added, each trail lists
the fallback links as missing, and the page ends with a table of them (`source.iter`, `source.fact_ref`,
`evidence.iter`, `veto.evidence_refs`, `veto.refute_confidence`, `credence.before_after`, `outcome.iter`,
`decision.vetoed`, `web_ideas.iter`, `source.query`, `v2.outcome_move`). A current run lists none of them;
only `v2.fact_check` remains for every v2 run, because the v2 loop has no fact-check step.

**Committed results today.** No committed run under `results/` records a web veto or any Exa source:
every report's `sources` is empty or absent, and all were written before the link fields. So
`demo.py --trail` reports the fifth moment as MISSING. A live run with `EXA_API_KEY` and shared memory on
is needed to fill it.

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
fact, so a BID with no SETTLE is not counted as an error, and in write order a SETTLE is paired with the
agent's latest BID on that candidate (an earlier one was withdrawn; the v2 loop re-bids on an unfunded
candidate in a later iteration).

**In the v2 loop.** `autoresearch research --allocation market --gpu-budget-s 3600 --target-llm openai-compat
...` gives every agent wallet 3600 GPU-seconds (`Wallets(..., gpu_initial=3600)`). A pre-registration sets it
with `"gpu_budget_s": 3600` (grid.py maps it to the flag like any other `research` option). The CLI refuses
the flag without `--allocation market`, with `--setting agentic` (the Petri harness runs the target in its
own process, where this run cannot meter it), or when the target is not GPU-metered (no `llm.GpuMeter`).
Without the flag, the run is unchanged (same wallets file, ledger, facts and report).

With a GPU budget the loop (`research/loop.py`):

* sizes each **supporting** bid's `gpu_s` as the GPU time the design will use if it is measured in full,
  at the GPU-seconds per sample observed so far: `samples` (x items in multi-item mode) x the dev
  target's rate, plus `screen_samples` x the screening target's rate when screening runs on a separate
  target (before a screening sample is seen: dev rate x `screen_cost`). The baseline is measured first,
  so the rate is known before the first bid. The request is capped at the agent's free GPU balance
  (`Market.gpu_available`); an agent with none left asks for the full amount, the market refuses it, and
  the agent cannot fund the design. The critic's bids against never ask for GPU time. If no GPU time has
  been observed (the target is not metered), bids stay dollar-only;
* wraps each candidate's screening, full measurement and, when it is accepted, its confirmation in
  `GpuUsage.measure(move)`, so a design is charged everything spent on it (confirmation is not part of
  the request);
* passes the measured seconds to `market.settle(..., gpu_seconds=...)`. A candidate whose bids are all
  withdrawn (not funded, or still deferred at the end) is not settled: its measured time moves to
  `report["market"]["gpu"]["unsettled_gpu_s"]`, so a later re-test starts from zero. The report also gives
  `gpu_initial`, `budget_gpu_s` (all GPU time this run, including the baseline) and `gpu_s_per_sample`.

## 3. The user model bids on which experiments run

Pipeline step 4. In a taste arm (`--taste-mode model`) with `--allocation market`, the user model is a
bidder (agent `user_model`) next to the sub-agents (proposer, scout, contrarian, ablation, critic). So the
order in which candidate experiments are measured comes from the researcher's taste and the sub-agents'
bids together.

* **Its bid.** For each gated design, P(validated) = `user_model_p(prior, taste, weight)`: the D1 taste
  score, ln(k x P(the user picks this design of k)), shifts the log-odds of the memory's prior for the
  design. The shift is scaled by the loop's learned taste weight (`Calibration.weight`). An indifferent user
  model (score 0) does not bid.
* **Advisory, not funding.** The bid enters the stake-weighted consensus P like any other. It adds no
  supporting stake (`Market.priority`), so a design is still funded by the agent that brought it. The user
  model moves the order in proportion to how far its belief departs from the others' and to its stake.
  It never asks for GPU time.
* **Earned influence.** It is settled by log score like every bid, so its wallet, its stake and its say
  over what gets measured grow only while its taste keeps predicting which experiments validate. Its BID
  and SETTLE facts go to shared memory and pass `market audit`.
* **Ablation.** `--no-user-model-bids` (`ResearchConfig.user_model_bids=False`) keeps taste in the D1
  ranking but takes it out of the market. R0 has no user model, so E5 (taste mode `none`) is unchanged.

```bash
python3 -m autoresearch research --taste-mode model --allocation market ...          # user model bids
python3 -m autoresearch research --taste-mode model --allocation market --no-user-model-bids ...
```

## Tests

```bash
python3 -m unittest tests.test_trail tests.test_market tests.test_demo
python3 -m unittest discover -s tests -t .
```

`tests/test_trail.py` runs the real v1 loop (with a stand-in fact-checking scout and a local shared
memory) and the real v2 loop (with an Exa-origin idea), then checks that every link of the trail is
joined on its exact key with nothing missing, that the same artifacts stripped of the link fields fall
back to the older joins and list them as missing, the HTML and the demo's fifth moment.
`tests/test_market_loop.py` runs the v2 loop with a GPU budget and a fake GPU-metered target (a
fake-clock `GpuMeter`), checks that BID/SETTLE facts carry the requested and measured GPU-seconds and that
`python3 -m autoresearch.research.market audit` passes on the ledger, and that a run without a budget is
unchanged. The GPU and audit tests measure no real GPU time. `TestUserModelBidsInTheLoop` checks that
a taste arm's user model bids and settles, that R0, prompt-only taste and `--no-user-model-bids` place no
user-model bids, and that its bids change which experiments are funded.
