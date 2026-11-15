"""How the `research` command shows a run in the terminal: the setup panel, live
per-iteration progress and the final results. Formatting only; nothing here
changes what the loop does or what goes into the report."""
from __future__ import annotations

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
