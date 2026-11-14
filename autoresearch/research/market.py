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
           a candidate and stakes credits from its wallet. Candidates are
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

Standard library only. Ledger facts (`BID`, `SETTLE`) go to shared memory
when one is attached, so every agent's track record is auditable across
workers and runs.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ALLOCATIONS = ("uniform", "halving", "market")
P_FLOOR = 0.05              # bids are clipped to [P_FLOOR, 1 - P_FLOOR]: a loss is at most stake * ln(10)
INITIAL_CREDITS = 100.0


def clip_p(p: float) -> float:
    return max(P_FLOOR, min(1.0 - P_FLOOR, float(p)))


@dataclass
class Bid:
    """One agent's claim about one candidate. `against` marks a bid that may
    lower the consensus but never funds a candidate (the critic)."""
    agent: str
    candidate_id: str
    p_validated: float
    exp_delta: float = 0.0
    stake: float = 1.0
    against: bool = False

    def __post_init__(self):
        if not self.agent or not self.candidate_id:
            raise ValueError("a bid needs an agent and a candidate_id")
        if not 0.0 <= float(self.p_validated) <= 1.0:
            raise ValueError(f"p_validated must be in [0, 1], got {self.p_validated}")
        if self.stake < 0:
            raise ValueError(f"stake must be non-negative, got {self.stake}")
        self.p_validated = clip_p(self.p_validated)


def log_score_payoff(p_validated: float, outcome: bool, stake: float) -> float:
    """stake * ln(q / 0.5): positive when the bid beat a coin flip on what happened."""
    q = clip_p(p_validated) if outcome else 1.0 - clip_p(p_validated)
    return stake * math.log(q / 0.5)


class Wallets:
    """Credit balances per agent, persisted across runs as JSON
    (`<memory>/wallets.json`). A balance never goes below zero."""

    def __init__(self, path: Optional[str] = None, initial: float = INITIAL_CREDITS):
        self.path, self.initial = path, initial
        self.data: Dict[str, dict] = {}
        if path and os.path.exists(path):
            with open(path) as f:
                self.data = json.load(f)

    def _row(self, agent: str) -> dict:
        return self.data.setdefault(agent, {"balance": self.initial, "settled": 0, "payoff": 0.0,
                                            "log_score": 0.0})

    def balance(self, agent: str) -> float:
        return self._row(agent)["balance"]

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
        return {a: {"balance": round(r["balance"], 4), "settled": r["settled"],
                    "payoff": round(r["payoff"], 4),
                    "mean_log_score": round(r["log_score"] / r["settled"], 4) if r["settled"] else None}
                for a, r in sorted(self.data.items())}


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
    """Bids, funding order, settlement and the ledger for one run."""

    def __init__(self, wallets: Optional[Wallets] = None, shared=None, run_id: str = "",
                 stake_frac: float = 0.1, min_stake: float = 0.5):
        if not 0 < stake_frac <= 1:
            raise ValueError(f"stake_frac must be in (0, 1], got {stake_frac}")
        self.wallets = wallets or Wallets()
        self.shared, self.run_id = shared, run_id
        self.stake_frac, self.min_stake = stake_frac, min_stake
        self.open: Dict[Tuple[str, str], Bid] = {}   # (agent, candidate) -> bid awaiting an outcome
        self.ledger: List[dict] = []

    # ---------- bidding ----------
    def stake_for(self, agent: str) -> float:
        """An agent stakes a fixed share of its balance: a good track record buys
        influence, a bad one shrinks it. Below `min_stake` it cannot bid."""
        bal = self.wallets.balance(agent)
        return 0.0 if bal < self.min_stake else max(self.min_stake, self.stake_frac * bal)

    def bid(self, agent: str, candidate_id: str, p_validated: float, exp_delta: float = 0.0,
            against: bool = False, it: Optional[int] = None) -> Optional[Bid]:
        """Place a bid with the agent's standard stake. A candidate keeps one open
        bid per agent (a deferred candidate's earlier bid stands); an agent with
        no credits left cannot bid."""
        if (agent, candidate_id) in self.open:
            return self.open[(agent, candidate_id)]
        stake = self.stake_for(agent)
        if stake <= 0:
            self.ledger.append({"event": "bid_refused", "iter": it, "agent": agent, "candidate": candidate_id,
                                "balance": round(self.wallets.balance(agent), 4)})
            return None
        b = Bid(agent, candidate_id, p_validated, exp_delta, stake, against)
        self.open[(agent, candidate_id)] = b
        self.ledger.append({"event": "bid", "iter": it, **asdict(b)})
        if self.shared:
            from ..integrations.shared_memory import format_fact
            self.shared.write("market", format_fact(
                "BID", agent=agent, candidate=candidate_id, p=round(b.p_validated, 4), stake=round(stake, 4),
                exp_delta=round(exp_delta, 4), against=against, run=self.run_id))
        return b

    def bids_on(self, candidate_id: str) -> List[Bid]:
        return [b for (_, c), b in self.open.items() if c == candidate_id]

    def consensus(self, candidate_id: str) -> Optional[float]:
        """Stake-weighted mean P(validated) over all open bids, critic included."""
        bs = [b for b in self.bids_on(candidate_id) if b.stake > 0]
        tot = sum(b.stake for b in bs)
        return sum(b.stake * b.p_validated for b in bs) / tot if tot else None

    def priority(self, candidate_id: str, cost: float = 1.0) -> float:
        """Funding priority = consensus P x supporting stake / cost (PLAN 8.3)."""
        p = self.consensus(candidate_id)
        support = sum(b.stake for b in self.bids_on(candidate_id) if not b.against)
        return 0.0 if p is None or cost <= 0 else p * support / cost

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
    def settle(self, outcomes: Dict[str, bool], it: Optional[int] = None) -> Dict[str, float]:
        """Pay every open bid on a candidate with a known outcome; returns
        agent -> total credit change. Wallets are saved after each settlement."""
        changes: Dict[str, float] = {}
        for key in [k for k in self.open if k[1] in outcomes]:
            b = self.open.pop(key)
            ok = bool(outcomes[b.candidate_id])
            ls = math.log(b.p_validated if ok else 1.0 - b.p_validated)
            change = self.wallets.apply(b.agent, log_score_payoff(b.p_validated, ok, b.stake), ls)
            changes[b.agent] = changes.get(b.agent, 0.0) + change
            bal = self.wallets.balance(b.agent)
            self.ledger.append({"event": "settle", "iter": it, "agent": b.agent, "candidate": b.candidate_id,
                                "p_validated": b.p_validated, "stake": b.stake, "outcome": ok,
                                "payoff": round(change, 6), "balance": round(bal, 4)})
            if self.shared:
                from ..integrations.shared_memory import format_fact
                self.shared.write("market", format_fact(
                    "SETTLE", agent=b.agent, candidate=b.candidate_id, outcome=ok, p=round(b.p_validated, 4),
                    payoff=round(change, 4), balance=round(bal, 4), run=self.run_id))
        if changes:
            self.wallets.save()
        return changes

    def withdraw(self, keep: Iterable[str] = (), it: Optional[int] = None) -> int:
        """Drop open bids on candidates that were never funded (no outcome, no
        payoff), except those in `keep` (deferred to the next iteration)."""
        keep = set(keep)
        gone = [k for k in self.open if k[1] not in keep]
        for k in gone:
            b = self.open.pop(k)
            self.ledger.append({"event": "withdraw", "iter": it, "agent": b.agent, "candidate": b.candidate_id})
        return len(gone)

    def report(self) -> dict:
        settled = [e for e in self.ledger if e["event"] == "settle"]
        return {"wallets": self.wallets.summary(), "n_bids": sum(e["event"] == "bid" for e in self.ledger),
                "n_settled": len(settled), "n_open": len(self.open),
                "brier": (round(sum((e["p_validated"] - e["outcome"]) ** 2 for e in settled) / len(settled), 4)
                          if settled else None),
                "ledger": self.ledger}
