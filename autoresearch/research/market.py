"""Resource market for evaluation samples (PLAN 8 and 12.5, experiment E5).

Most of the cost of a run is evaluation samples, so the loop has to decide
which candidate designs get measured and how much. Three allocation modes,
the arms of E5:

  uniform  the first `evals_per_iter` candidates in priority order each get
           `samples` samples (the loop's behaviour before the market).
  halving  plain successive halving over the same priority order: every
           candidate the budget allows gets a few screening samples, the top
           half gets the rest of a full measurement.
  market   successive halving where the order comes from bids. Each agent
           (proposer, contrarian, scout, critic, ...) states P(validated) for
           a candidate and stakes credits from its wallet. In a taste arm the
           user model bids too (`bid_user_model`): its taste score shifts the
           memory's prior, so which experiments run first depends on the
           researcher's taste and the sub-agents' bids together, and the
           user model's weight is earned in the same way. Candidates are
           funded in order of consensus P x supporting stake / cost. Once the
           outcome is known, every bid is paid its log score against it,
           scaled by its stake, so calibrated agents gain credits (and with
           them influence) and over-confident ones lose them.

Settlement uses the log scoring rule relative to an uninformed coin flip:
payoff = stake * ln(q / 0.5), with q the probability the bid gave to what
happened. The log rule is strictly proper, so an agent maximises its expected
credits by reporting its true belief (PLAN I16); tests check this by
simulation. The market only reorders and sizes measurement: it never decides
what counts as validated, which stays with the loop's statistics.

GPU time (Modal + past.dev). A run on the self-hosted target (an open-weight
model served by vLLM, `llm.OpenAICompatLLM`) is billed per GPU-second, not per
sample. When the wallets have a GPU budget (`Wallets(gpu_initial=...)`), a
bidder may also ask for GPU-seconds for its candidate (`Market.bid(...,
gpu_s=...)`). The request is checked against the agent's GPU balance (minus
its other open requests), but what settlement charges is the MEASURED busy
time of the target (`GpuUsage`, which reads `Budget.gpu_seconds`, charged by
`llm.GpuMeter`), split among the candidate's GPU bidders in proportion to
their requests. The credit payoff (log score) is unchanged. GPU `BID` and
`SETTLE` facts carry `resource=gpu_s` and the requested and measured seconds,
so `audit_ledger` can replay every agent's credit and GPU balance from shared
memory. Where one currency is needed, GPU-seconds convert to dollars at
OPENAI_COMPAT_USD_PER_HOUR (`gpu_s_to_usd`). Without a GPU budget nothing
changes: same wallets file, same ledger entries, same facts.

Standard library only. Ledger facts (`BID`, `SETTLE`) go to shared memory
when one is attached, so every agent's track record is auditable across
workers and runs (`audit_ledger`, or `python3 -m autoresearch.research.market
audit <shared.jsonl>`).
"""
from __future__ import annotations

import argparse
import json
import math
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ALLOCATIONS = ("uniform", "halving", "market")
P_FLOOR = 0.05              # bids are clipped to [P_FLOOR, 1 - P_FLOOR]: a loss is at most stake * ln(10)
INITIAL_CREDITS = 100.0
RESOURCES = ("usd", "gpu_s")   # usd: the existing credit bids on sample budget; gpu_s: self-hosted target time
RATE_ENV = "OPENAI_COMPAT_USD_PER_HOUR"   # the same rate llm.OpenAICompatLLM bills GPU time at
USER_MODEL = "user_model"   # the researcher's user model, bidding alongside the sub-agents (bid_user_model)


def clip_p(p: float) -> float:
    return max(P_FLOOR, min(1.0 - P_FLOOR, float(p)))


# ---------- dollars <-> GPU-seconds ----------
def usd_per_gpu_hour(rate: Optional[float] = None) -> Optional[float]:
    """The GPU rate in $/hour: `rate` if given, else OPENAI_COMPAT_USD_PER_HOUR
    (the rate the self-hosted target is billed at). None when neither is set:
    GPU-seconds then have no dollar value and nothing is converted."""
    raw = rate if rate is not None else os.environ.get(RATE_ENV)
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{RATE_ENV} must be a number, got {raw!r}")
    if value < 0:
        raise ValueError(f"{RATE_ENV} must be >= 0, got {value}")
    return value


def gpu_s_to_usd(seconds: float, usd_per_hour: float) -> float:
    return float(seconds) * float(usd_per_hour) / 3600.0


def usd_to_gpu_s(usd: float, usd_per_hour: float) -> float:
    if not usd_per_hour:
        raise ValueError("converting dollars to GPU-seconds needs a positive $/hour rate")
    return float(usd) * 3600.0 / float(usd_per_hour)


@dataclass
class Bid:
    """One agent's claim about one candidate. `against` marks a bid that may
    lower the consensus but never funds a candidate (the critic).

    `resource="gpu_s"` marks a bid that also asks for `gpu_s` GPU-seconds of
    the self-hosted target for the candidate's run; the stake is credits
    either way."""
    agent: str
    candidate_id: str
    p_validated: float
    exp_delta: float = 0.0
    stake: float = 1.0
    against: bool = False
    resource: str = "usd"
    gpu_s: float = 0.0

    def __post_init__(self):
        if not self.agent or not self.candidate_id:
            raise ValueError("a bid needs an agent and a candidate_id")
        if not 0.0 <= float(self.p_validated) <= 1.0:
            raise ValueError(f"p_validated must be in [0, 1], got {self.p_validated}")
        if self.stake < 0:
            raise ValueError(f"stake must be non-negative, got {self.stake}")
        if self.resource not in RESOURCES:
            raise ValueError(f"resource must be one of {RESOURCES}, got {self.resource!r}")
        if self.resource == "gpu_s":
            if not self.gpu_s > 0:
                raise ValueError(f"a gpu_s bid needs a positive gpu_s request, got {self.gpu_s}")
            if self.against:
                raise ValueError("a bid against a candidate never funds it, so it cannot ask for GPU time")
        elif self.gpu_s:
            raise ValueError("gpu_s is only meaningful with resource='gpu_s'")
        self.p_validated = clip_p(self.p_validated)

    def ledger_fields(self) -> dict:
        """The bid as a ledger entry; a dollar bid keeps the original fields only."""
        d = asdict(self)
        if self.resource == "usd":
            d.pop("resource")
            d.pop("gpu_s")
        return d


def user_model_p(prior: float, taste_score: float, weight: float = 1.0) -> float:
    """P(validated) the user model states for a candidate.

    `taste_score` is the loop's D1 score, ln(k x P(the user picks this one of
    k)): 0 when the user model is indifferent, positive when it prefers the
    candidate to an average one. It shifts the log-odds of `prior` (the
    memory's credence that the candidate validates), scaled by `weight` (the
    loop's learned taste reliability, 0 = ignore taste). So an indifferent or
    unreliable user model states the prior and a confident one moves away
    from it, in the direction of its preference."""
    q = clip_p(prior)
    return clip_p(1.0 / (1.0 + math.exp(-(math.log(q / (1.0 - q)) + weight * taste_score))))


def log_score_payoff(p_validated: float, outcome: bool, stake: float) -> float:
    """stake * ln(q / 0.5): positive when the bid beat a coin flip on what happened."""
    q = clip_p(p_validated) if outcome else 1.0 - clip_p(p_validated)
    return stake * math.log(q / 0.5)


class Wallets:
    """Credit balances per agent, persisted across runs as JSON
    (`<memory>/wallets.json`). A balance never goes below zero.

    With `gpu_initial` (GPU-seconds per agent) each wallet also holds a GPU
    budget: `gpu_s` left, `gpu_s_spent` charged so far (measured), and
    `gpu_s_unpaid`, measured time the agent's balance could not cover.
    Without it the wallets file has exactly the credit fields."""

    def __init__(self, path: Optional[str] = None, initial: float = INITIAL_CREDITS,
                 gpu_initial: Optional[float] = None):
        if gpu_initial is not None and gpu_initial < 0:
            raise ValueError(f"gpu_initial must be non-negative, got {gpu_initial}")
        self.path, self.initial, self.gpu_initial = path, initial, gpu_initial
        self.data: Dict[str, dict] = {}
        if path and os.path.exists(path):
            with open(path) as f:
                self.data = json.load(f)

    @property
    def gpu_enabled(self) -> bool:
        return self.gpu_initial is not None

    def _row(self, agent: str) -> dict:
        row = self.data.setdefault(agent, {"balance": self.initial, "settled": 0, "payoff": 0.0,
                                           "log_score": 0.0})
        if self.gpu_enabled and "gpu_s" not in row:   # a wallet from a dollar-only run gets its GPU budget now
            row.update(gpu_s=float(self.gpu_initial), gpu_s_spent=0.0, gpu_s_unpaid=0.0)
        return row

    def balance(self, agent: str) -> float:
        return self._row(agent)["balance"]

    def gpu_balance(self, agent: str) -> float:
        if not self.gpu_enabled:
            raise ValueError("no GPU budget configured (Wallets(gpu_initial=...))")
        return self._row(agent)["gpu_s"]

    def charge_gpu(self, agent: str, seconds: float) -> float:
        """Charge measured GPU-seconds; returns the amount actually deducted
        (the GPU balance never goes below zero, the rest is recorded as unpaid)."""
        if seconds < 0:
            raise ValueError(f"measured GPU-seconds must be non-negative, got {seconds}")
        row = self._row(agent) if self.gpu_enabled else None
        if row is None:
            raise ValueError("no GPU budget configured (Wallets(gpu_initial=...))")
        charged = min(float(seconds), row["gpu_s"])
        row["gpu_s"] -= charged
        row["gpu_s_spent"] += charged
        row["gpu_s_unpaid"] += float(seconds) - charged
        return charged

    def apply(self, agent: str, payoff: float, log_score: float) -> float:
        """Add a settlement; returns the change actually applied (clipped at zero balance)."""
        row = self._row(agent)
        new = max(0.0, row["balance"] + payoff)
        change = new - row["balance"]
        row["balance"] = new
        row["settled"] += 1
        row["payoff"] += change
        row["log_score"] += log_score
        return change

    def save(self) -> None:
        if not self.path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

    def summary(self) -> Dict[str, dict]:
        out = {}
        for a, r in sorted(self.data.items()):
            out[a] = {"balance": round(r["balance"], 4), "settled": r["settled"],
                      "payoff": round(r["payoff"], 4),
                      "mean_log_score": round(r["log_score"] / r["settled"], 4) if r["settled"] else None}
            if "gpu_s" in r:
                out[a].update(gpu_s=round(r["gpu_s"], 4), gpu_s_spent=round(r["gpu_s_spent"], 4),
                              gpu_s_unpaid=round(r["gpu_s_unpaid"], 4))
        return out


class GpuUsage:
    """Measured GPU-seconds per candidate on the self-hosted target.

    `OpenAICompatLLM` charges its endpoint's busy time, from `llm.GpuMeter`,
    to `Budget.gpu_seconds`; `measure(candidate)` records how much that grew
    while the candidate was being measured. Measurements must not overlap
    (the loop measures candidates one after another). Like GpuMeter, this is
    a lower bound on the bill: idle time and cold starts are not seen."""

    def __init__(self, budget):
        if not hasattr(budget, "gpu_seconds"):
            raise TypeError("GpuUsage needs an llm.Budget (it reads Budget.gpu_seconds)")
        self.budget = budget
        self.seconds: Dict[str, float] = {}
        self._active: Optional[str] = None

    @contextmanager
    def measure(self, candidate_id: str):
        if self._active is not None:
            raise RuntimeError(f"GPU measurement of {self._active!r} is still open; measurements cannot overlap")
        self._active, before = candidate_id, float(self.budget.gpu_seconds)
        try:
            yield
        finally:
            self._active = None
            self.seconds[candidate_id] = self.seconds.get(candidate_id, 0.0) + (
                float(self.budget.gpu_seconds) - before)

    def pop(self, candidate_ids: Iterable[str]) -> Dict[str, float]:
        """Measured seconds for these candidates (removed, so a re-test starts from zero)."""
        return {c: self.seconds.pop(c) for c in list(candidate_ids) if c in self.seconds}


def halving_plan(n_available: int, budget: int, full: int, screen: int = 2,
                 merged: bool = True, screen_cost: float = 1.0) -> Tuple[int, int]:
    """(candidates screened, survivors) for one round of successive halving.

    Screening gives each of n candidates `screen` samples; the top max(1, n // 2)
    are then brought up to a full measurement of `full` samples. With
    `merged` the screening samples count toward the full measurement (same
    target); without it (a cheaper screening target, cost `screen_cost` per
    sample relative to the dev target) survivors get `full` fresh samples.
    n is the largest that fits in `budget` dev-target samples; at least one
    candidate is always measured in full."""
    if n_available <= 0:
        return 0, 0
    if not 0 < screen < full and merged:
        raise ValueError(f"screen samples must be in (0, full={full}) when merged, got {screen}")

    def cost(n):
        keep = max(1, n // 2)
        return n * screen + keep * (full - screen) if merged else n * screen * screen_cost + keep * full
    n = 1
    while n < n_available and cost(n + 1) <= budget:
        n += 1
    return n, max(1, n // 2)


class Market:
    """Bids, funding order, settlement and the ledger for one run.

    `usd_per_hour` is the GPU rate used where dollars and GPU-seconds must be
    compared (default OPENAI_COMPAT_USD_PER_HOUR; None leaves GPU time
    unpriced)."""

    def __init__(self, wallets: Optional[Wallets] = None, shared=None, run_id: str = "",
                 stake_frac: float = 0.1, min_stake: float = 0.5, usd_per_hour: Optional[float] = None):
        if not 0 < stake_frac <= 1:
            raise ValueError(f"stake_frac must be in (0, 1], got {stake_frac}")
        self.wallets = wallets or Wallets()
        self.shared, self.run_id = shared, run_id
        self.stake_frac, self.min_stake = stake_frac, min_stake
        self._usd_per_hour = usd_per_hour
        self.open: Dict[Tuple[str, str], Bid] = {}   # (agent, candidate) -> bid awaiting an outcome
        self.ledger: List[dict] = []

    @property
    def usd_per_hour(self) -> Optional[float]:
        """Resolved when GPU time is priced, so a dollar-only market never reads the env var."""
        return usd_per_gpu_hour(self._usd_per_hour)

    # ---------- bidding ----------
    def stake_for(self, agent: str) -> float:
        """An agent stakes a fixed share of its balance: a good track record buys
        influence, a bad one shrinks it. Below `min_stake` it cannot bid."""
        bal = self.wallets.balance(agent)
        return 0.0 if bal < self.min_stake else max(self.min_stake, self.stake_frac * bal)

    def gpu_requested(self, agent: str) -> float:
        """GPU-seconds the agent has asked for in bids that are still open."""
        return sum(b.gpu_s for (a, _), b in self.open.items() if a == agent)

    def gpu_available(self, agent: str) -> float:
        """GPU balance not already asked for by the agent's open bids."""
        return self.wallets.gpu_balance(agent) - self.gpu_requested(agent)

    def bid(self, agent: str, candidate_id: str, p_validated: float, exp_delta: float = 0.0,
            against: bool = False, it: Optional[int] = None, gpu_s: Optional[float] = None) -> Optional[Bid]:
        """Place a bid with the agent's standard stake. A candidate keeps one open
        bid per agent (a deferred candidate's earlier bid stands); an agent with
        no credits left cannot bid.

        `gpu_s` asks for that many GPU-seconds of the self-hosted target for
        the candidate (needs a GPU budget in the wallets). It is refused when
        it exceeds the agent's GPU balance minus its other open requests; at
        settlement the agent pays the measured time, not this request."""
        if (agent, candidate_id) in self.open:
            return self.open[(agent, candidate_id)]
        gpu = gpu_s is not None
        if gpu and not self.wallets.gpu_enabled:
            raise ValueError("a gpu_s bid needs a GPU budget (Wallets(gpu_initial=...))")
        stake = self.stake_for(agent)
        refusal = None
        if stake <= 0:
            refusal = "credits"
        elif gpu and float(gpu_s) > self.gpu_available(agent) + 1e-9:
            refusal = "gpu_s"
        if refusal:
            ev = {"event": "bid_refused", "iter": it, "agent": agent, "candidate": candidate_id,
                  "balance": round(self.wallets.balance(agent), 4)}
            if gpu:
                ev.update(resource="gpu_s", reason=refusal, gpu_s_bid=round(float(gpu_s), 4),
                          gpu_s_available=round(self.gpu_available(agent), 4))
            self.ledger.append(ev)
            return None
        b = Bid(agent, candidate_id, p_validated, exp_delta, stake, against,
                *(("gpu_s", float(gpu_s)) if gpu else ()))
        self.open[(agent, candidate_id)] = b
        self.ledger.append({"event": "bid", "iter": it, **b.ledger_fields()})
        if self.shared:
            from ..integrations.shared_memory import format_fact
            extra = {}
            if gpu:
                extra = {"resource": "gpu_s", "gpu_s_bid": round(b.gpu_s, 4),
                         "gpu_balance": round(self.wallets.gpu_balance(agent), 4)}
            self.shared.write("market", format_fact(
                "BID", agent=agent, candidate=candidate_id, p=round(b.p_validated, 4), stake=round(stake, 4),
                exp_delta=round(exp_delta, 4), against=against, run=self.run_id, **extra))
        return b

    def bid_user_model(self, candidate_id: str, prior: float, taste_score: float, weight: float = 1.0,
                       it: Optional[int] = None) -> Optional[Bid]:
        """The user model's bid (agent USER_MODEL), so experiments are funded on
        the researcher's taste and the sub-agents' bids together.

        P(validated) is `user_model_p(prior, taste_score, weight)`. The bid is
        advisory: it enters the stake-weighted consensus P like any bid, but
        adds no supporting stake (`priority`), so a candidate is still funded
        by the agent that brought it, and the user model moves the order in
        proportion to how far its belief departs from the others' and to its
        stake. With no preference (a zero shift) it does not bid: a bid at the
        prior would carry no information. The bid is settled like any other,
        so the user model's stake, and with it its say over what gets
        measured, grows only while its taste keeps predicting which
        experiments validate. It never asks for GPU time: that is requested by
        the agent that brought the candidate."""
        if abs(weight * taste_score) < 1e-9:
            return None
        return self.bid(USER_MODEL, candidate_id, user_model_p(prior, taste_score, weight), it=it)

    def bids_on(self, candidate_id: str) -> List[Bid]:
        return [b for (_, c), b in self.open.items() if c == candidate_id]

    def consensus(self, candidate_id: str) -> Optional[float]:
        """Stake-weighted mean P(validated) over all open bids, critic included."""
        bs = [b for b in self.bids_on(candidate_id) if b.stake > 0]
        tot = sum(b.stake for b in bs)
        return sum(b.stake * b.p_validated for b in bs) / tot if tot else None

    def priority(self, candidate_id: str, cost: float = 1.0) -> float:
        """Funding priority = consensus P x supporting stake / cost (PLAN 8.3).
        Supporting stake comes from the agents that brought the candidate; the
        critic's bids against it and the user model's advisory bid move only
        the consensus."""
        p = self.consensus(candidate_id)
        support = sum(b.stake for b in self.bids_on(candidate_id) if not b.against and b.agent != USER_MODEL)
        return 0.0 if p is None or cost <= 0 else p * support / cost

    def cost_usd(self, candidate_id: str, usd: float = 0.0) -> Optional[float]:
        """One-currency cost estimate for funding order: `usd` (the candidate's
        API cost) plus the largest GPU request among its open bids, priced at
        `usd_per_hour`. None when GPU time is requested but no rate is set."""
        gpu = max((b.gpu_s for b in self.bids_on(candidate_id) if b.resource == "gpu_s"), default=0.0)
        if not gpu:
            return float(usd)
        rate = self.usd_per_hour
        return None if rate is None else float(usd) + gpu_s_to_usd(gpu, rate)

    def order(self, candidate_ids: Sequence[str], costs: Optional[Dict[str, float]] = None) -> List[str]:
        """Candidates with supporting stake, highest priority first (stable on ties)."""
        costs = costs or {}
        pri = {c: self.priority(c, costs.get(c, 1.0)) for c in candidate_ids}
        return [c for c in sorted(candidate_ids, key=lambda c: -pri[c]) if pri[c] > 0]

    def allocate(self, bids: Iterable[Bid], budget_samples: int, full: int, screen: int = 2,
                 costs: Optional[Dict[str, float]] = None) -> Dict[str, int]:
        """Round-1 allocation {candidate_id: screening samples} for bids already
        placed with `bid` (or given here). Survivors are chosen with `survivors`
        once the screening samples are in."""
        for b in bids:
            self.open.setdefault((b.agent, b.candidate_id), b)
        order = self.order(sorted({b.candidate_id for b in self.open.values()}), costs)
        n, _ = halving_plan(len(order), budget_samples, full, screen)
        return {c: screen for c in order[:n]}

    # ---------- settlement ----------
    def settle(self, outcomes: Dict[str, bool], it: Optional[int] = None,
               gpu_seconds: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Pay every open bid on a candidate with a known outcome; returns
        agent -> total credit change. Wallets are saved after each settlement.

        `gpu_seconds` maps a candidate to the GPU-seconds MEASURED for its run
        (`GpuUsage`). It is required for every settled candidate with a GPU
        bid; the measured time is split among those bids in proportion to the
        seconds each asked for and charged to the bidders' GPU balances."""
        gpu_seconds = gpu_seconds or {}
        keys = [k for k in self.open if k[1] in outcomes]
        gpu_cands = sorted({k[1] for k in keys if self.open[k].resource == "gpu_s"})
        missing = [c for c in gpu_cands if c not in gpu_seconds]
        if missing:   # checked before anything is paid, so a bad call changes nothing
            raise ValueError(f"settling GPU bids needs measured GPU-seconds for {missing}")
        for c in gpu_cands:
            if gpu_seconds[c] < 0:
                raise ValueError(f"measured GPU-seconds for {c!r} must be non-negative, got {gpu_seconds[c]}")
        requested = {c: sum(self.open[k].gpu_s for k in keys if k[1] == c and self.open[k].resource == "gpu_s")
                     for c in gpu_cands}
        rate = self.usd_per_hour if gpu_cands else None
        changes: Dict[str, float] = {}
        for key in keys:
            b = self.open.pop(key)
            ok = bool(outcomes[b.candidate_id])
            ls = math.log(b.p_validated if ok else 1.0 - b.p_validated)
            change = self.wallets.apply(b.agent, log_score_payoff(b.p_validated, ok, b.stake), ls)
            changes[b.agent] = changes.get(b.agent, 0.0) + change
            bal = self.wallets.balance(b.agent)
            entry = {"event": "settle", "iter": it, "agent": b.agent, "candidate": b.candidate_id,
                     "p_validated": b.p_validated, "stake": b.stake, "outcome": ok,
                     "payoff": round(change, 6), "balance": round(bal, 4)}
            extra = {}
            if b.resource == "gpu_s":
                measured = float(gpu_seconds[b.candidate_id])
                share = measured * b.gpu_s / requested[b.candidate_id]
                charged = self.wallets.charge_gpu(b.agent, share)
                gbal = self.wallets.gpu_balance(b.agent)
                extra = {"resource": "gpu_s", "gpu_s": round(share, 4), "gpu_s_bid": round(b.gpu_s, 4),
                         "gpu_s_measured": round(measured, 4), "gpu_charged": round(charged, 4),
                         "gpu_balance": round(gbal, 4)}
                if rate is not None:
                    extra["usd_equiv"] = round(gpu_s_to_usd(share, rate), 6)
                entry.update(extra)
            self.ledger.append(entry)
            if self.shared:
                from ..integrations.shared_memory import format_fact
                self.shared.write("market", format_fact(
                    "SETTLE", agent=b.agent, candidate=b.candidate_id, outcome=ok, p=round(b.p_validated, 4),
                    payoff=round(change, 4), balance=round(bal, 4), run=self.run_id, **extra))
        if changes:
            self.wallets.save()
        return changes

    def withdraw(self, keep: Iterable[str] = (), it: Optional[int] = None) -> int:
        """Drop open bids on candidates that were never funded (no outcome, no
        payoff), except those in `keep` (deferred to the next iteration). A
        withdrawn GPU request is released without charge: nothing was run."""
        keep = set(keep)
        gone = [k for k in self.open if k[1] not in keep]
        for k in gone:
            b = self.open.pop(k)
            self.ledger.append({"event": "withdraw", "iter": it, "agent": b.agent, "candidate": b.candidate_id})
        return len(gone)

    def report(self) -> dict:
        settled = [e for e in self.ledger if e["event"] == "settle"]
        out = {"wallets": self.wallets.summary(), "n_bids": sum(e["event"] == "bid" for e in self.ledger),
               "n_settled": len(settled), "n_open": len(self.open),
               "brier": (round(sum((e["p_validated"] - e["outcome"]) ** 2 for e in settled) / len(settled), 4)
                         if settled else None),
               "ledger": self.ledger}
        if self.wallets.gpu_enabled:
            gpu = [e for e in settled if e.get("resource") == "gpu_s"]
            measured = sum(e["gpu_s"] for e in gpu)
            rate = self.usd_per_hour
            out["gpu"] = {"usd_per_hour": rate,
                          "n_bids": sum(e["event"] == "bid" and e.get("resource") == "gpu_s" for e in self.ledger),
                          "n_settled": len(gpu), "gpu_s_measured": round(measured, 4),
                          "gpu_s_charged": round(sum(e["gpu_charged"] for e in gpu), 4),
                          "usd_equiv": round(gpu_s_to_usd(measured, rate), 6) if rate is not None else None}
        return out


# ---------- ledger audit (past.dev) ----------
def _f(d: dict, k: str) -> Optional[float]:
    try:
        return float(d[k])
    except (KeyError, TypeError, ValueError):
        return None


def ledger_facts(source, query: str = "BID SETTLE market", limit: int = 100000) -> Tuple[List[dict], bool]:
    """(BID and SETTLE facts, whether they are in write order) from a local
    shared-memory JSONL path (file order = write order) or any SharedMemory
    (`recall` order, which is not write order: only per-fact checks apply)."""
    from ..integrations.shared_memory import parse_fact
    path = source if isinstance(source, str) else getattr(source, "path", None)
    if path:   # a local store: read the file itself, in write order
        out = []
        with open(path) as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                f = parse_fact(row.get("content", "")) if isinstance(row, dict) else None
                if f and f["kind"] in ("BID", "SETTLE"):
                    out.append({**f, "_ref": f"{os.path.basename(path)}:{n}"})
        return out, True
    out = []
    for n, r in enumerate(source.recall("auditor", query, limit)):
        f = parse_fact(r.get("content", ""))
        if f and f["kind"] in ("BID", "SETTLE"):
            out.append({**f, "_ref": f"recall:{n}"})
    return out, False


def _payoff_tol(stake: float) -> float:
    # facts round p, stake, payoff and balance to 4 decimals; d/dp ln(p) <= 1/P_FLOOR
    return 5e-4 + stake * 1.2e-3


def audit_ledger(facts: Iterable[dict], ordered: bool = True, initial: Optional[float] = INITIAL_CREDITS,
                 gpu_initial: Optional[float] = None, run: Optional[str] = None,
                 wallets: Optional[Dict[str, dict]] = None) -> dict:
    """Replay BID/SETTLE facts and check every agent's balance and track record.

    Checks, per SETTLE fact: a BID by the same agent on the same candidate in
    the same run precedes it (its stake is used; with ordered facts, the latest
    such BID, since earlier ones were withdrawn, which writes no fact); the credit change equals
    stake * ln(q / 0.5) (clipped at a zero balance); with `ordered` facts, the
    balance follows from the agent's previous SETTLE (or `initial` for its
    first; initial=None takes the first balance as given, for wallets carried
    over from earlier runs). GPU facts (resource=gpu_s): the request fit the
    agent's GPU balance, the measured shares of a candidate add up to its
    measured total, and the GPU balance falls by exactly what was charged.
    `wallets` (a `Wallets.summary()` or wallets.json rows) is compared with
    the replayed final balances and settled counts. Returns the per-agent
    track record and a list of problems (empty = the ledger is consistent)."""
    facts = [f for f in facts if f.get("kind") in ("BID", "SETTLE") and (run is None or f.get("run", "") == run)]
    problems: List[dict] = []
    agents: Dict[str, dict] = {}
    open_bids: Dict[Tuple[str, str, str], List[dict]] = {}
    credit: Dict[str, float] = {}
    gpu: Dict[str, float] = {}
    gpu_groups: Dict[Tuple[str, str, str], List[dict]] = {}   # one settlement of one candidate's GPU bids

    def problem(f, check, detail):
        problems.append({"ref": f.get("_ref"), "kind": f.get("kind"), "agent": f.get("agent"),
                         "candidate": f.get("candidate"), "run": f.get("run", ""), "check": check, "detail": detail})

    def row(a):
        return agents.setdefault(a, {"n_bids": 0, "n_settled": 0, "payoff": 0.0, "log_score": 0.0, "brier": 0.0,
                                     "balance": None, "gpu_s_bid": 0.0, "gpu_s_measured": 0.0,
                                     "gpu_charged": 0.0, "gpu_balance": None})

    for f in facts:
        a, cand, rn = f.get("agent", ""), f.get("candidate", ""), f.get("run", "")
        r = row(a)
        is_gpu = f.get("resource") == "gpu_s"
        if f["kind"] == "BID":
            r["n_bids"] += 1
            open_bids.setdefault((rn, a, cand), []).append(f)
            stake = _f(f, "stake")
            if ordered and stake is not None and credit.get(a) is not None and stake > credit[a] + 1e-3:
                problem(f, "stake_within_balance", f"stake {stake} exceeds balance {credit[a]}")
            if is_gpu:
                req, gb = _f(f, "gpu_s_bid"), _f(f, "gpu_balance")
                r["gpu_s_bid"] += req or 0.0
                if req is None or gb is None:
                    problem(f, "gpu_fields", "a gpu_s BID needs gpu_s_bid and gpu_balance")
                    continue
                if ordered:
                    prev = gpu.get(a, gpu_initial)
                    if prev is not None and abs(prev - gb) > 1e-3:
                        problem(f, "gpu_balance_chain", f"BID states GPU balance {gb}, replay has {prev}")
                    gpu[a] = gb
                if req > gb + 1e-3:
                    problem(f, "gpu_request_within_balance", f"asked for {req} GPU-s with {gb} left")
                r["gpu_balance"] = gb
            continue
        # SETTLE. The market keeps one open bid per agent and candidate, and a withdrawal writes no
        # fact, so in write order the bid being settled is the latest BID: earlier ones were withdrawn.
        queue = open_bids.get((rn, a, cand)) or []
        bid = (queue[-1] if ordered else queue[0]) if queue else None
        if ordered:
            queue.clear()
        elif queue:
            queue.pop(0)
        if bid is None:
            problem(f, "bid_before_settle", "no earlier BID by this agent on this candidate in this run"
                    + ("" if ordered else " (facts unordered: the BID may simply not have been recalled)"))
        p, payoff, bal = _f(f, "p"), _f(f, "payoff"), _f(f, "balance")
        outcome = f.get("outcome") == "True"
        if p is None or payoff is None or bal is None:
            problem(f, "settle_fields", "SETTLE needs p, payoff and balance")
            continue
        r["n_settled"] += 1
        r["payoff"] += payoff
        q = p if outcome else 1.0 - p
        r["log_score"] += math.log(max(q, 1e-12))
        r["brier"] += (p - (1.0 if outcome else 0.0)) ** 2
        stake = _f(bid, "stake") if bid else None
        if bid is not None and _f(bid, "p") is not None and abs(_f(bid, "p") - p) > 1e-4:
            problem(f, "settle_matches_bid", f"SETTLE p={p} but BID p={_f(bid, 'p')}")
        if stake is not None:
            expected = log_score_payoff(p, outcome, stake)
            prev = credit.get(a, initial) if ordered else None
            if prev is not None:
                applied = max(0.0, prev + expected) - prev
                if abs(applied - payoff) > _payoff_tol(stake):
                    problem(f, "payoff_is_log_score", f"payoff {payoff}, expected {applied:.4f} "
                            f"(stake {stake} x ln({q:.4f}/0.5), from balance {prev})")
                if abs(prev + payoff - bal) > 1e-3:
                    problem(f, "balance_chain", f"balance {bal}, previous {prev} + payoff {payoff}")
            elif abs(expected - payoff) > _payoff_tol(stake) and not (bal <= 1e-4 and payoff > expected):
                problem(f, "payoff_is_log_score", f"payoff {payoff}, expected {expected:.4f}")
        credit[a] = bal
        r["balance"] = bal
        if is_gpu or (bid is not None and bid.get("resource") == "gpu_s"):
            share, measured = _f(f, "gpu_s"), _f(f, "gpu_s_measured")
            charged, gbal = _f(f, "gpu_charged"), _f(f, "gpu_balance")
            if None in (share, measured, charged, gbal) or not is_gpu:
                problem(f, "gpu_fields", "a SETTLE of a gpu_s bid needs resource=gpu_s, gpu_s, gpu_s_measured, "
                                         "gpu_charged and gpu_balance")
                continue
            r["gpu_s_measured"] += share
            r["gpu_charged"] += charged
            gpu_groups.setdefault((rn, cand, f.get("gpu_s_measured")), []).append(f)
            if charged > share + 1e-3:
                problem(f, "gpu_charge_is_measured", f"charged {charged} GPU-s for a measured share of {share}")
            if ordered:
                prev = gpu.get(a, gpu_initial)
                if prev is not None:
                    if abs(min(share, prev) - charged) > 1e-3:
                        problem(f, "gpu_charge_is_measured", f"charged {charged}, measured share {share}, "
                                f"balance before {prev}")
                    if abs(prev - charged - gbal) > 1e-3:
                        problem(f, "gpu_balance_chain", f"GPU balance {gbal}, previous {prev} - charged {charged}")
                gpu[a] = gbal
            r["gpu_balance"] = gbal
    for (rn, cand, _), group in gpu_groups.items():
        measured = _f(group[0], "gpu_s_measured")
        total = sum(_f(g, "gpu_s") for g in group)
        if abs(total - measured) > 1e-3 * max(1, len(group)):
            problem(group[0], "gpu_shares_add_up", f"shares sum to {total:.4f} of {measured} measured GPU-s "
                    f"on {cand}" + ("" if ordered else " (facts unordered: some may not have been recalled)"))
    # A BID left without a SETTLE was withdrawn or is still open: withdrawals write no fact, so it is not an error.
    summary = {}
    for a, r in sorted(agents.items()):
        n = r["n_settled"]
        summary[a] = {"n_bids": r["n_bids"], "n_settled": n, "payoff": round(r["payoff"], 4),
                      "balance": r["balance"], "mean_log_score": round(r["log_score"] / n, 4) if n else None,
                      "brier": round(r["brier"] / n, 4) if n else None}
        if r["gpu_s_bid"] or r["gpu_balance"] is not None:
            summary[a].update(gpu_s_bid=round(r["gpu_s_bid"], 4), gpu_s_measured=round(r["gpu_s_measured"], 4),
                              gpu_charged=round(r["gpu_charged"], 4), gpu_balance=r["gpu_balance"])
    for a, w in sorted((wallets or {}).items()):
        got = summary.get(a)
        ref = {"_ref": "wallets", "kind": "WALLET", "agent": a}
        if got is None:
            if w.get("settled"):
                problem(ref, "wallet_matches_ledger", f"wallet has {w['settled']} settlements, the ledger none")
            continue
        if ordered and got["balance"] is not None and abs(float(w["balance"]) - got["balance"]) > 1e-3:
            problem(ref, "wallet_matches_ledger", f"wallet balance {w['balance']}, ledger replay {got['balance']}")
        if w.get("settled") is not None and int(w["settled"]) != got["n_settled"]:
            problem(ref, "wallet_matches_ledger", f"wallet settled {w['settled']}, ledger {got['n_settled']} "
                    "(a wallet carried over from runs not in this ledger also differs)")
        if ordered and "gpu_s" in w and got.get("gpu_balance") is not None \
                and abs(float(w["gpu_s"]) - got["gpu_balance"]) > 1e-3:
            problem(ref, "wallet_matches_ledger", f"wallet GPU balance {w['gpu_s']}, ledger {got['gpu_balance']}")
    return {"ok": not problems, "ordered": ordered, "n_facts": len(facts),
            "n_bid": sum(f["kind"] == "BID" for f in facts), "n_settle": sum(f["kind"] == "SETTLE" for f in facts),
            "agents": summary, "problems": problems}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m autoresearch.research.market",
                                 description="Market ledger tools (offline; reads files only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    au = sub.add_parser("audit", help="replay BID/SETTLE facts from a local shared-memory JSONL")
    au.add_argument("shared", help="shared-memory JSONL (e.g. <memory>/shared.jsonl)")
    au.add_argument("--wallets", help="wallets.json to compare with the replay")
    au.add_argument("--run", help="only this run's facts")
    au.add_argument("--initial", type=float, default=INITIAL_CREDITS,
                    help="starting credit balance (default %(default)s)")
    au.add_argument("--carried-over", action="store_true",
                    help="wallets started from an earlier run: take each agent's first balance as given")
    au.add_argument("--gpu-initial", type=float, help="starting GPU-seconds per agent, if a GPU budget was set")
    args = ap.parse_args(argv)
    facts, ordered = ledger_facts(args.shared)
    wallets = None
    if args.wallets:
        with open(args.wallets) as fh:
            wallets = json.load(fh)
    rep = audit_ledger(facts, ordered=ordered, initial=None if args.carried_over else args.initial,
                       gpu_initial=args.gpu_initial, run=args.run, wallets=wallets)
    print(json.dumps(rep, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
