"""How the `research` command shows a run in the terminal: the setup panel, live
per-iteration progress and the final results. Formatting only; nothing here
changes what the loop does or what goes into the report."""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from ..ui import Console

STATUS_STYLE = {
    "validated": ("green", "bold"), "unconfirmed": ("yellow",), "deferred": ("yellow",),
    "rejected": ("red",), "invalid": ("magenta",), "drifted": ("gray",),
}


def _num(x, digits: int = 3) -> str:
    return "-" if x is None else f"{x:.{digits}f}"


def signed(c: Console, x: Optional[float], digits: int = 3, higher_is_better: bool = True) -> str:
    """A signed number, green when it moves the right way and red when it doesn't."""
    if x is None:
        return c.style("-", "dim")
    text = f"{x:+.{digits}f}"
    if abs(x) < 10 ** -digits:
        return c.style(text, "dim")
    good = (x > 0) == higher_is_better
    return c.style(text, "green" if good else "red")


def status(c: Console, st: str) -> str:
    return c.style(st, *STATUS_STYLE.get(st, ()))


def prob(c: Console, p: Optional[float], threshold: Optional[float] = None) -> str:
    if p is None:
        return c.style("-", "dim")
    text = f"{p:.2f}"
    return c.style(text, "bold", "green") if threshold is not None and p >= threshold else text


def setup_panel(c: Console, s: Dict) -> str:
    """The run's configuration. ``s`` holds the values `cmd_research` resolved."""
    on = lambda v: c.style(v, "green") if v not in (None, "off", "none") else c.style("off", "dim")
    corpus = f"{s['corpus_n']} msgs " + (c.style("topic-matched", "green") if s["matched"]
                                         else c.style("NOT topic-matched", "yellow"))
    models = (f"generator {c.style(s['generator'], 'bold')}  target {c.style(s['target'], 'bold')}  "
              f"judge {c.style(s['judge'], 'bold')}  {c.style('(' + s['llm'] + ')', 'dim')}")
    researcher = c.style(s["researcher"], "bold") + (c.style(f"  user model: {s['user_model']}", "dim")
                                                     if s.get("user_model") else "")
    alloc = s["allocation"] + (c.style(f"  screen {s['screen']}", "dim") if s.get("screen") else "")
    rows = [
        ("arm", c.style(s["arm"], "bold", "magenta") + c.style(f"  taste mode {s['taste_mode']}", "dim")),
        ("researcher", researcher),
        ("models", models),
        ("setting", f"{s['setting']}  {c.style('scenario', 'gray')} {c.style(s['scenario'], 'bold')}"),
        ("items", s.get("items")),
        ("real corpus", corpus if s["setting"] == "single" else None),
        ("allocation", alloc),
        ("contrarian", str(s["contrarian"]) if s.get("contrarian") else None),
        ("web", on(s["web"])),
        ("shared memory", on(s["shared"])),
    ]
    return c.panel(c.kv(rows), title="AutoResearch · research loop", style="cyan")


def _scores_table(c: Console, rep: Dict) -> str:
    b, f = rep["baseline"], rep["best"]
    rows = []
    for key, label, better_up in (("score", "score", True), ("awareness", "awareness", False),
                                  ("validity", "validity", True)):
        bv, fv = b.get(key), f.get(key)
        d = None if bv is None or fv is None else fv - bv
        rows.append([c.style(label, "bold"), _num(bv), c.style(_num(fv), "bold"),
                     signed(c, d, higher_is_better=better_up), c.bar(fv, 12, "green" if better_up else "yellow")])
    ci = lambda e: f"[{e['ci90'][0]:.2f}, {e['ci90'][1]:.2f}]" if e.get("ci90") else "-"
    rows.append([c.style("score 90% CI", "dim"), c.style(ci(b), "dim"), c.style(ci(f), "dim"), "", ""])
    return c.table(["", "baseline", "best", "Δ", ""], rows, align="<>>><")


def findings_table(c: Console, findings: List[Dict], accept_p: Optional[float] = None) -> str:
    def change(x):   # category on the first line (kept in colour), the intervention text below it
        removed = str(x.get("move", "")).startswith("remove")
        return [c.style(("remove " if removed else "") + x.get("category", ""), "cyan"), x.get("text", "")]
    rows = [[c.style(x["id"], "dim"), str(x["iter"]), status(c, x["status"]), signed(c, x.get("delta")),
             prob(c, x.get("p_better"), accept_p), _num(x.get("validity"), 2), _num(x.get("awareness"), 2),
             change(x)]
            for x in findings]
    return c.table(["id", "it", "status", "Δ score", "P(better)", "valid", "aware", "intervention"],
                   rows, align="<><>>>><", flex=7)


def results(c: Console, rep: Dict, report_path: str, decisions_path: Optional[str] = None) -> str:
    """Everything the run found, in the order a reader wants it."""
    out = ["", c.rule("Results", "green")]
    if rep.get("aborted"):
        out.append(c.style(f"Run aborted early: {rep['aborted']}", "bold", "red"))
    for w in rep.get("measurer_warnings") or []:
        out.append(c.style("warning: ", "bold", "yellow") + w)
    out.append(_scores_table(c, rep))
    p = rep.get("p_best_beats_baseline")
    accept_p = (rep.get("config") or {}).get("accept_p")
    out.append(f"  P(best beats baseline) = {prob(c, p, accept_p or 0.9)}")
    design = rep.get("best_design") or []
    if design:
        out += ["", c.style("Best design", "bold")]
        out += [f"  {c.style(c.box['bullet'], 'green')} {c.style(i.get('category', ''), 'cyan')}  {i.get('text', '')}"
                for i in design]
    else:
        out += ["", c.style("Best design: the baseline (no intervention was validated)", "dim")]

    fs = rep.get("findings") or []
    if fs:
        n_val = sum(x["status"] == "validated" for x in fs)
        counts: Dict[str, int] = {}
        for x in fs:
            counts[x["status"]] = counts.get(x["status"], 0) + 1
        tally = "  ".join(f"{status(c, k)} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
        out += ["", c.style("Findings", "bold") + f"  {c.style(str(n_val), 'bold', 'green')} validated of "
                f"{len(fs)} tested   {c.style('(', 'dim')}{tally}{c.style(')', 'dim')}"]
        out.append(findings_table(c, fs, accept_p))
    if rep.get("abandoned_directions"):
        out.append(c.style("abandoned directions: ", "gray") + ", ".join(map(str, rep["abandoned_directions"])))

    out += ["", c.panel(c.kv(_detail_rows(c, rep)), title="Taste · claims · checks", style="blue")]
    cm = rep.get("compute") or {}
    compute = "  ".join([
        f"{c.style(str(cm.get('calls', 0)), 'bold')} calls",
        f"{cm.get('input_tokens', 0):,} in / {cm.get('output_tokens', 0):,} out tokens",
        c.style(f"${cm.get('cost_usd', 0.0):.2f}", "bold"),
        f"{cm.get('wall_seconds', cm.get('seconds', 0.0)):.1f}s"])
    out += c.kv([("compute", compute),
                 ("decisions", c.style(decisions_path, "underline") if decisions_path else None),
                 ("report", c.style(report_path, "underline"))])
    return "\n".join(out)


def _detail_rows(c: Console, rep: Dict) -> List[tuple]:
    t = rep.get("taste") or {}
    rows = []
    if t:
        al = t.get("alignment")
        rows.append(("taste", "  ".join([
            f"alignment {c.style(_num(al, 2) if isinstance(al, (int, float)) else str(al), 'bold')}",
            f"rho {signed(c, t.get('reliability_rho'), 2)}",
            f"weight {c.style(_num(t.get('effective_weight'), 2), 'bold')}"])))
    cl = rep.get("claims") or {}
    if cl:
        k, n = len(cl.get("included", [])), cl.get("n", 0)
        rows.append(("claims", f"{c.style(f'{k}/{n}', 'bold', 'green' if k == n else 'yellow')} supported  "
                               f"{c.style('pass rate ' + str(cl.get('pass_rate')), 'dim')}"))
    for key, fa in (rep.get("faithfulness") or {}).items():
        rows.append((f"faithfulness {key}", f"{fa['misbehavior']} as-is {c.style(str(fa['rate_plain']), 'bold')}  "
                                            f"with eval notice {c.style(str(fa['rate_eval_notice']), 'bold')}  "
                                            f"{c.style('n=' + str(fa['n']), 'dim')}"))
    for key, per in (rep.get("realism_auroc") or {}).items():
        rows.append((f"realism AUROC {key}",
                     "  ".join(w + " " + c.style(_num(v["auroc"]), "bold") for w, v in per.items())))
    mk = rep.get("market")
    if mk:
        wallets = "  ".join(a + " " + c.style(_num(w["balance"], 1), "bold") for a, w in mk["wallets"].items())
        rows.append(("market", wallets + "  " + c.style(
            f"bids {mk['n_bids']}, settled {mk['n_settled']}, Brier {mk['brier']}", "dim")))
    al = rep.get("allocation") or {}
    if al:
        rows.append(("samples", f"{al.get('samples', 0)} measured"
                                + (f", {al['screen_samples']} screening" if al.get("screen_samples") else "")))
    return rows or [("details", c.style("none recorded", "dim"))]


class Progress:
    """Prints the loop's events as they happen. Pass an instance as
    ``OpenResearcher(progress=...)``."""

    WARN = {"exa_error": "web search failed", "explain_error": "explanations (D5) failed",
            "claims_error": "claim extraction (D6) failed", "setting_check_error": "setting check failed"}

    def __init__(self, c: Console, accept_p: Optional[float] = None, confirm_p: Optional[float] = None,
                 events_path: Optional[str] = None):
        self.c, self.accept_p, self.confirm_p = c, accept_p, confirm_p
        self.best: Optional[float] = None
        # Every event (with A1/A2 summaries) appended as it happens, so a run that is
        # killed before it writes its report still leaves its measurements on disk.
        self.events_path = events_path

    def _append_event(self, ev: Dict) -> None:
        try:
            with open(self.events_path, "a") as fh:
                fh.write(json.dumps(ev, default=str) + "\n")
        except OSError as e:   # a full disk must not stop the run; say so once and stop trying
            self.c.print(self.c.style("  warning ", "bold", "yellow") + f"cannot write {self.events_path}: {e}")
            self.events_path = None

    def __call__(self, ev: Dict) -> None:
        if self.events_path:
            self._append_event(ev)
        handler = getattr(self, "_on_" + str(ev.get("event")), None)
        if handler is not None:
            handler(ev)
        elif ev.get("event") in self.WARN:
            detail = ev.get("detail") or ev.get("error") or ""
            self.c.print(self.c.style("  warning ", "bold", "yellow") + f"{self.WARN[ev['event']]}: {detail}")

    def _metrics(self, ev: Dict) -> str:
        c = self.c
        return (f"score {c.style(_num(ev.get('score')), 'bold')}  awareness {_num(ev.get('awareness'))}  "
                f"validity {_num(ev.get('validity'))}  {self._a1a2(ev)}  {c.style('n=' + str(ev.get('n')), 'dim')}")

    @staticmethod
    def _a1a2(ev: Dict) -> str:
        """A1 = verbalized (says unprompted it is being evaluated), A2 = self-reported P(eval)."""
        return f"A1 {_num(ev.get('verbalized'), 2)}  A2 {_num(ev.get('self_report'), 2)}"

    def _on_baseline(self, ev: Dict) -> None:
        self.best = ev.get("score")
        self.c.print("\n" + self.c.style("baseline ", "bold", "cyan") + " " + self._metrics(ev))

    def _on_iteration(self, ev: Dict) -> None:
        self.c.print("\n" + self.c.rule(f"iteration {ev['iter']}/{ev['of']}", "blue"))

    def _on_web_ideas(self, ev: Dict) -> None:
        self.c.print(self.c.style(f"  web     {len(ev.get('ideas', []))} new ideas from search", "dim"))

    def _on_allocation(self, ev: Dict) -> None:
        if ev.get("screened"):
            self.c.print(self.c.style(f"  screen  {ev['screened']} candidates screened ({ev.get('mode')})", "dim"))

    def _on_gated_refuted_category(self, ev: Dict) -> None:
        self.c.print(self.c.style(f"  skip    {ev.get('category')}: category already refuted", "dim"))

    def _on_evaluated(self, ev: Dict) -> None:
        c = self.c
        idea = ev.get("idea") or {}
        removed = str(ev.get("move", "")).startswith("remove")
        head = (c.style("  measure ", "gray") + c.style(("remove " if removed else "") + idea.get("category", ""), "cyan")
                + f"  Δ {signed(c, ev.get('delta'))}  P(better) {prob(c, ev.get('p_better'), self.accept_p)}  "
                + f"validity {_num(ev.get('validity'), 2)}  awareness {_num(ev.get('awareness'), 2)}")
        c.print(head)
        a1a2 = self._a1a2(ev) + " · "
        c.print(c.style("          " + a1a2 + c.truncate(idea.get("text", ""), c.width - 10 - len(a1a2)), "dim"))

    def _on_confirmation(self, ev: Dict) -> None:
        c = self.c
        ok = self.confirm_p is not None and ev.get("p_better", 0) >= self.confirm_p
        c.print(c.style("  confirm ", "gray") + "fresh samples  P(better) "
                + c.style(_num(ev.get("p_better"), 2), "bold", "green" if ok else "yellow") + "  " + self._a1a2(ev))

    def _on_setting_drift(self, ev: Dict) -> None:
        self.c.print(self.c.style("  drift   ", "bold", "yellow") + f"{ev.get('category')}: {ev.get('why')}")

    def _on_abandoned_direction(self, ev: Dict) -> None:
        self.c.print(self.c.style("  abandon ", "bold", "yellow") + f"{ev.get('category')} (mixed results)")

    def _on_budget_exhausted(self, ev: Dict) -> None:
        self.c.print("\n" + self.c.style(f"budget exhausted before iteration {ev.get('iter')}", "bold", "yellow"))

    def _on_aborted(self, ev: Dict) -> None:
        self.c.print("\n" + self.c.style(f"aborted: {ev.get('error')}", "bold", "red"))

    def _on_progress(self, ev: Dict) -> None:
        if not ev.get("iter"):
            return
        c = self.c
        fs = ev.get("findings") or []
        if fs:
            c.print(c.style("  outcome ", "gray") + "  ".join(
                c.style(f.get("category", ""), "cyan") + " " + status(c, f["status"]) for f in fs))
        score = ev.get("best_score")
        moved = score is not None and self.best is not None and score > self.best + 1e-9
        best = c.style(_num(score), "bold", "green" if moved else "")
        if moved:
            best += " " + signed(c, score - self.best)
        self.best = score if score is not None else self.best
        cost = ev.get("cost_usd")
        c.print(c.style("  best    ", "gray") + best + c.style(
            f"   {ev.get('validated', 0)} validated · {ev.get('samples', 0)} samples · {ev.get('calls') or 0} calls"
            + (f" · ${cost:.2f}" if cost is not None else "")
            + (f" · {ev['seconds']:.0f}s" if ev.get("seconds") is not None else ""), "dim"))
