# Personal-track trade-off questionnaire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the personal track's D1-only intervention seed pairs with a trade-off questionnaire (stance + scenario items over 13 eval-design axes, D1–D6), with optional LLM-written scenarios gated by a balance check.

**Architecture:** A hand-written bank (`data/trackp/tradeoffs.jsonl`) and a new module `autoresearch/taste/tradeoffs.py` (load the bank, build pairs, LLM scenarios, balance check). `trackp.py` keeps storage, answering and the CLI; its `seed-pairs` calls the new module, `pending` orders and filters seed items, and two commands (`balance`, `review`) are added.

**Tech Stack:** Python 3 standard library, `unittest`, the repo's `llm.get_llm` and `taste.methods.create_method`.

**Spec:** `docs/superpowers/specs/2026-11-14-trackp-tradeoff-questionnaire-design.md`

## Global Constraints

- No Hobbhahn material in any item: no source in the bank may be by Marius Hobbhahn or Apollo Research.
- Every pair is a trade-off: both options defensible, similar length and specificity, no evaluative words ("better", "rigorous", "sloppy").
- `Choice`, `UserModel.fit`, `split`, labels and recheck are unchanged. The split stays uniform per pair by hashing `pair_id`.
- No reason is asked for, anywhere (terminal or agent). A volunteered reason may still be passed with `--reason`.
- Default `--n 50` = 13 stance + 37 scenario items.
- Pending seed order: scenario items grouped by item (items in file order), stance items last.
- Never show the person the axis, poles, theme or decision point.
- LLM scenarios and the balance check are paid unless `--llm offline`/`--backend offline`; off by default.
- Balance threshold default 0.8, checker default method `m0`.
- Tests: `python3 -m unittest discover -s tests -t .`. WS B owns `trackp.py`; take an `agentctl` lock on it and on `autoresearch/taste/tradeoffs.py` before editing.

## Review Focus

- `--n` below 13: only stance items, the first n in bank order, no crash. (Task 1 test.)
- Re-running `seed-pairs` with a larger `--n`: earlier pairs and answers kept, only new pair ids appended. (Task 2 test.)
- An LLM reply that is not JSON, or returns two identical options: that pair is skipped with a warning, the rest are kept. (Task 3 test.)
- `record` on an LLM pair that hasn't passed the balance check: refused as "not pending". (Task 3 test.)
- A pair flagged one-sided and then dropped in review never reappears in `pending`, and an approved one does. (Task 3 test.)

---

### Task 1: The trade-off bank and pair builders

**Files:**
- Create: `data/trackp/tradeoffs.jsonl`
- Create: `autoresearch/taste/tradeoffs.py`
- Test: `tests/test_tradeoffs.py`

**Interfaces:**
- Produces:
  - `BANK_PATH = "data/trackp/tradeoffs.jsonl"`
  - `load_bank(path: str = BANK_PATH) -> List[dict]`, which validates rows (raises `ValueError` naming the axis and the missing field).
  - `stance_pairs(bank: List[dict]) -> List[dict]`
  - `scenario_pairs(bank: List[dict], items: list, n: int, seed: int = 0) -> List[dict]`, with `items` as `Scenario` objects.
  - `build_seed_pairs(bank, items, n: int, seed: int = 0) -> List[dict]`: stance first, up to `n`, then scenarios filling the rest.
  - `scenario_context(sc) -> str`: the item lines of today's `trackp.item_context` without its question.
  - Pair row: `{"pair_id", "form": "stance"|"scenario", "axis", "decision_point", "origin": "bank"|"llm", "item": str|None, "context", "a_text", "b_text", "a_pole": 1|2, "b_pole": 1|2}`. `pair_id = digest([form, axis, item or "", a_text, b_text])[:12]`, using `usermodel.digest`. Each pair's a/b order is randomised with `random.Random(seed)`, and the poles record which side is which.
  - Bank row fields: `axis, decision_point, sources (list), question, pole_1, pole_2, scenario_question, scenario_1, scenario_2`.

- [ ] **Step 1: Write the bank.** One row for each of the 13 axes in the spec's table (`construct-scope` … `openness`), with the spec's decision point and sources. Stance `question` is in the general form ("When you design an eval, which do you lean towards?"). `scenario_question` and `scenario_1`/`scenario_2` read against an item context ("For this environment, …"). Follow the Global Constraints wording rules.

- [ ] **Step 2: Write the failing tests** in `tests/test_tradeoffs.py`:
  - `test_bank_has_thirteen_axes_covering_d1_to_d6`: 13 distinct axes, `{r["decision_point"]} == {"D1",…,"D6"}`.
  - `test_bank_cites_no_hobbhahn_or_apollo_source`: no source matches `re.compile("hobbhahn|apollo", re.I)`.
  - `test_load_bank_names_the_axis_with_a_missing_field`: a temp bank missing `pole_2` raises a `ValueError` whose message contains the axis.
  - `test_default_fifty_is_thirteen_stance_and_thirty_seven_scenarios`: uses `SCENARIOS["metric_inflation"]` and `SCENARIOS["fabrication"]`; counts 13/37; distinct `pair_id`s; scenario items split evenly over the two items (±1), with every axis appearing.
  - `test_n_below_thirteen_gives_only_stance_items`: `n=5` gives 5 stance rows, in bank order.
  - `test_poles_track_the_shuffled_option_order`: for every row, `{a_pole, b_pole} == {1, 2}`, and the text at pole 1 equals the bank's `pole_1` (stance) or `scenario_1` (scenario).
  - `test_scenario_context_has_the_item_and_the_axis_question`: contains `sc.goal` and the row's `scenario_question`; stance context contains no item goal.
  - `test_same_seed_same_pairs`.

- [ ] **Step 3: Run** `python3 -m unittest tests.test_tradeoffs -v`. Expected: FAIL (`No module named autoresearch.taste.tradeoffs`).

- [ ] **Step 4: Implement** `tradeoffs.py` per the Interfaces block. `scenario_pairs` builds all (axis, item) combos, shuffles them with `random.Random(seed)`, then takes them round-robin over items, the same way `trackp.make_seed_pairs` does today.

- [ ] **Step 5: Run** `python3 -m unittest tests.test_tradeoffs -v`. Expected: PASS.

- [ ] **Step 6: Commit** `data/trackp/tradeoffs.jsonl autoresearch/taste/tradeoffs.py tests/test_tradeoffs.py`. Message: "WS B personal track: trade-off bank and stance/scenario pair builders".

### Task 2: Wire the questionnaire into trackp

**Files:**
- Modify: `autoresearch/taste/trackp.py`. Remove `QUESTION`, `item_context` and `make_seed_pairs`. Change `_seed_items`, `record`, `ask_items` and the `seed-pairs` CLI branch. Update the module docstring.
- Test: `tests/test_trackp.py`

**Interfaces:**
- Consumes: `tradeoffs.load_bank`, `tradeoffs.build_seed_pairs`, and the Task 1 pair row.
- Produces:
  - Public seed item: `{"id": "seed:<pair_id>", "kind": "seed", "group": <item name or "stance">, "context", "evidence": {}, "options": [a_text, b_text]}`. The keys `_order` and `_src` stay private.
  - The seed `Choice` takes `decision_point` from the pair row, with no `group_id`.

- [ ] **Step 1: Update the test helpers and write the failing tests** in `tests/test_trackp.py`:
  - Replace `library_rank` with `pole_one(pairs_path)`, which returns a `prefer(text)` scoring 1 for any text that is pole 1 in the stored pairs. The person is consistent: they always pick pole 1.
  - Change `seed()` to call `seed-pairs` with `--scenarios metric_inflation fabrication`, as now.
  - `test_seed_pairs_default_to_stance_and_scenario_items`: `seed-pairs --n 20` writes 13 stance + 7 scenario rows.
  - `test_pending_groups_scenarios_by_item_and_puts_stance_last`: the `group` sequence of `pending --limit 1000` is non-decreasing in first-appearance order, and ends with all the `"stance"` items.
  - `test_pending_never_shows_axis_poles_or_decision_point`: no public item has the keys `axis`, `a_pole`, `b_pole` or `decision_point`, and no context contains an axis name.
  - Adapt `test_recorded_answers_are_choices_with_reasons_and_leave_nothing_pending`: each row's `decision_point` equals its pair's, and the winner is the pole-1 text.
  - `test_rerunning_seed_pairs_keeps_answers_and_appends_new_ids`: run with `--n 15`, answer everything, run again with `--n 30`. The first 15 answers are kept, and 15 new items are pending.
  - Adapt `test_terminal_loop_records_the_same_answer_as_record`: the scripted answers are only `["2"]`, with no "why?" prompt, and the stored `reason` is `""`.
  - Delete `test_seed_pairs_are_distinct_same_item_and_balanced`, which Task 1's tests now cover.

- [ ] **Step 2: Run** `python3 -m unittest tests.test_trackp -v`. Expected: FAIL on the new and adapted tests.

- [ ] **Step 3: Implement.**
  - `seed-pairs` loads the bank, builds the pairs with `_items(args)`, `--n` and `--seed`, then calls `write_seed_pairs`.
  - Remove `--llm-ideas`; Task 3 adds `--llm-scenarios`.
  - `_seed_items` sorts scenario rows by the first-appearance index of their item, keeping file order within each item, then appends the stance rows.
  - `record` sets `decision_point=src["decision_point"]`.
  - `ask_items` drops the reason prompt and passes `""`.
  - Leave `ideas.LIBRARY` untouched.

- [ ] **Step 4: Run** `python3 -m unittest discover -s tests -t .`. Expected: PASS, including the split, recheck, fit and e2 tests that use the new `seed()`.

- [ ] **Step 5: Commit** `autoresearch/taste/trackp.py tests/test_trackp.py`. Message: "WS B personal track: seed questionnaire uses the trade-off bank; grouped order; no reason prompt".

### Task 3: LLM scenarios, balance check and review

**Files:**
- Modify: `autoresearch/taste/tradeoffs.py`, `autoresearch/taste/trackp.py`
- Test: `tests/test_tradeoffs.py`, `tests/test_trackp.py`

**Interfaces:**
- Consumes: the Task 1 pair row; `LLM.complete(prompt, ...) -> str`; `llm.extract_json`, already used in `ideas.py`; `UserModel.predict(context, options) -> Prediction` with `.probabilities`.
- Produces:
  - `llm_scenario_pairs(bank, items, llm, k: int, seed: int = 0, warn=print) -> List[dict]`: for each item, k axes taken round-robin. The prompt asks for JSON `{"option_1": ..., "option_2": ...}`, one option per pole, of similar length and specificity, with no evaluative words. Rows get `origin: "llm"`.
  - `BALANCE = "balance.jsonl"`, in the person's directory, with rows `{"type": "check", "pair_id", "p_pole1": [p_ab, p_ba], "one_sided": bool, "method", "timestamp"}` or `{"type": "review", "pair_id", "decision": "approve"|"drop", "timestamp"}`.
  - `balance_check(pairs: List[dict], model, threshold: float = 0.8) -> List[dict]`: returns check rows. A pair is one-sided when the model gives the same pole a probability of at least `threshold` in both orders.
  - `shown(pair, balance_rows) -> bool`, true when no `drop` review exists and either: the pair is from the bank with no one-sided check; or it has a non-one-sided check; or it has an `approve` review. An LLM pair with no check is never shown.
  - CLI:
    - `seed-pairs --llm-scenarios K --llm <backend> --model <m> --max-calls N` adds LLM pairs alongside the `--n` bank pairs.
    - `balance --method m0 --backend <b> --model <m> --threshold 0.8 --max-calls N` checks every pair that has no check row yet and appends the rows.
    - `review` prints the flagged, unreviewed pairs as JSON. `review --id <pair_id> --decision approve|drop` appends a review row.
  - `_seed_items` filters with `shown`. `next_steps` adds "N LLM pair(s) need 'balance' (paid, ask first)" and "N flagged pair(s) need 'review' by someone other than the person answering".

- [ ] **Step 1: Write the failing tests.**
  - In `test_tradeoffs.py`, with a stub LLM whose `complete` returns queued strings:
    - `test_llm_scenarios_tag_poles_and_origin`.
    - `test_llm_reply_that_is_not_json_or_has_identical_options_is_skipped_with_a_warning`: two bad replies and one good one give one row and two warnings.
    - `test_balance_flags_a_pair_both_orders_favour_one_pole`: a stub `UserModel` subclass returns `[0.9, 0.1]` when pole 1 is first and `[0.1, 0.9]` when it is second, so the pair is flagged. A stub that always returns `[0.9, 0.1]` (position bias, not pole bias) is not flagged.
  - In `test_trackp.py`:
    - `test_llm_pairs_are_not_pending_until_balanced`: `record` on such a pair raises `SystemExit`.
    - `test_dropped_pair_never_returns_and_approved_pair_does`.
    - `test_status_asks_for_balance_then_review`.
  - Drive the LLM through the CLI with `--llm offline` only where offline output parses. Otherwise call the functions directly with stubs.

- [ ] **Step 2: Run** `python3 -m unittest tests.test_tradeoffs tests.test_trackp -v`. Expected: FAIL.

- [ ] **Step 3: Implement** per the Interfaces block. The `balance` CLI builds its model with `create_method(args.method, get_llm(...), ...)` the same way `fit` does, and does not fit it, since `m0` needs no history.

- [ ] **Step 4: Run** `python3 -m unittest discover -s tests -t .`. Expected: PASS.

- [ ] **Step 5: Commit** `autoresearch/taste/tradeoffs.py autoresearch/taste/trackp.py tests/test_tradeoffs.py tests/test_trackp.py`. Message: "WS B personal track: LLM-written scenarios, balance check and review".

### Task 4: Runbook, PLAN, pipeline diagram, WS A notice

**Files:**
- Modify: `docs/trackp-runbook.md` (§1 set-up, §2 collection, table at line ~49)
- Modify: `PLAN.md` §12.2 lines ~556–561 (seed choices), and line 304 (seed pairs row)
- Modify: `scripts/build_pipeline_diagram.py:43`, then regenerate `docs/pipeline/`

- [ ] **Step 1: Runbook.**
  - §1: `seed-pairs --n 50` makes 13 stance and 37 scenario items. `--llm-scenarios K` is paid, so ask first. Then `balance` (paid) and `review`, done by someone who isn't the person answering.
  - §2 "In chat (agents)": replace the steps with the spec's six administration rules, word for word in substance:
    - Tell the person up front: about 20 minutes, they can stop and resume, there are no right answers, and each question asks what they would do.
    - Show scenarios grouped by their `group` field: the context once, then each question. Stance items come last.
    - Never name the axis, the poles or the decision point.
    - No commentary on the options.
    - Record each answer at once. Don't ask why; record a reason only if the person volunteers one.
    - Offer a break at the halfway point, and run `status` at the end.
  - Remove "ask why in one sentence".

- [ ] **Step 2: PLAN.md.** Change the seed-pairs descriptions to: 13 trade-off axes from non-Hobbhahn eval-design primers, asked as stance and scenario items across D1–D6. Point to the spec.

- [ ] **Step 3: Diagram.** Change the stage label to `"trackp seed-pairs · trade-off bank; --llm-scenarios adds paid ones"`. Then run `python3 scripts/build_pipeline_diagram.py`. Expected: it exits 0, and `git diff --stat docs/pipeline` shows only the files that label touches.

- [ ] **Step 4: Run** `python3 -m unittest discover -s tests -t .`. Expected: PASS. Then commit the four paths. Message: "WS B personal track: runbook administration rules, PLAN and diagram for the trade-off questionnaire".

- [ ] **Step 5: Notify WS A.** Run `python3 scripts/agentctl.py post gio-a "Personal-track seed pairs are now trade-off items (stance + scenario, D1-D6), not intervention pairs; decision_point varies. If a feature-based method (M4) relied on D1 intervention pairs, tell me. Spec: docs/superpowers/specs/2026-11-14-trackp-tradeoff-questionnaire-design.md"`. Then push.
