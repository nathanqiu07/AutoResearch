"""Write one rewritten version of every dev seed per arm, with `claude -p --model sonnet`.

    python3 experiments/taste_petri/arms/make_arms.py R0 T1 T2 T3 T4 T5 G1

Each arm -> seeds/<arm>.jsonl (seed_id "<base>@<arm>", base_seed_id, text, len_ratio, meta). Calls are cached in
cache/ (proxy's CachedCLI), so re-runs are free; real CLI calls are appended to calls.log.
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
TP = HERE.parent
REPO = TP.parents[1]
sys.path.insert(0, str(TP / "proxy"))
from proxy_eval import CachedCLI, load_seeds  # noqa: E402

PROMPTS = HERE / "prompts"
PROFILES = TP / "profiles"
RESEARCHERS = ["samuel_bowman", "ryan_greenblatt", "buck_shlegeris", "evan_hubinger", "owain_evans"]
SEED_RE = re.compile(r"<seed>(.*?)</seed>", re.DOTALL)
OPS_RE = re.compile(r"<ops>(.*?)</ops>", re.DOTALL)
DAY_RE = re.compile(r"<day>(.*?)</day>", re.DOTALL)

llm = CachedCLI("sonnet", cache_dir=HERE / "cache")


def fill(template: str, **kw) -> str:
    text = (PROMPTS / template).read_text()
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def card(slug: str, fmt: str) -> str:
    """A profile file without its generator comment line."""
    f = next((PROFILES / slug).glob(f"{fmt}_*.md"))
    return "\n".join(l for l in f.read_text().splitlines() if not l.startswith("<!--")).strip()


def cap_of(n: int) -> int:
    # 1.3x stock; floor 600 chars so the 224-char seed_73 has room for any edit at all
    return max(int(1.3 * n), 600)


def common(n: int) -> str:
    return fill("common.txt", CAP=str(int(0.85 * cap_of(n))), N=str(n))


def rewrite(prompt: str, n: int) -> tuple[str, str]:
    """(seed text, raw reply). One retry if the reply has no <seed> or is over the cap."""
    raw = llm.complete(prompt, max_tokens=3000)
    m = SEED_RE.search(raw)
    if m and len(m.group(1).strip()) <= cap_of(n):
        return m.group(1).strip(), raw
    got = len(m.group(1).strip()) if m else 0
    fix = (f"{prompt}\n\nYour previous answer was:\n{raw}\n\n"
           + (f"It is {got} characters; the hard limit is {cap_of(n)}. Shorten it to at most {int(0.9 * cap_of(n))} "
              "characters without dropping the opportunity, the pressure or the monitoring instruction."
              if m else "It had no <seed>...</seed> block.")
           + " Return the edited seed between <seed> and </seed>.")
    raw2 = llm.complete(fix, max_tokens=3000)
    m2 = SEED_RE.search(raw2)
    if not m2:
        raise ValueError(f"no <seed> after retry: {raw2[:200]!r}")
    return m2.group(1).strip(), raw2


def realism_plans() -> dict:
    text = (TP / "ideas" / "realism.md").read_text()
    sec = text.split("## 4. Per-seed rewrite plans", 1)[1].split("## 5.", 1)[0]
    plans = {}
    for chunk in re.split(r"^### ", sec, flags=re.M)[1:]:
        sid = chunk.split(":", 1)[0].strip()
        body = re.split(r"^\*\*Test:\*\*", chunk, flags=re.M)[0]   # the test line is for us, not the rewriter
        plans[sid] = "### " + body.strip()
    return plans


def operators() -> str:
    out = HERE / "T2_operators.json"
    if not out.exists():
        cards = "\n\n".join(f"=== {s} ===\n{card(s, 'c')}" for s in RESEARCHERS)
        raw = llm.complete(fill("T2_compile.txt", CARDS=cards), max_tokens=8000)
        d = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        out.write_text(json.dumps(d, indent=1))
    return out.read_text()


def arm_one(arm: str, s: dict, plans: dict, ops_lib: str) -> dict:
    n, seed = len(s["text"]), s["text"]
    meta = {}
    if arm == "R0":
        prompt = fill("R0.txt", COMMON=common(n), SEED=seed)
    elif arm in ("T1", "T5"):
        owner = "samuel_bowman" if arm == "T1" else "owain_evans"
        prompt = fill("T1.txt", COMMON=common(n), CARD_OWNER=owner.replace("_", " ").title(), CARD=card(owner, "c"),
                      GUARD=card("ryan_greenblatt", "e"), SEED=seed)
    elif arm == "T2":
        prompt = fill("T2.txt", COMMON=common(n), OPERATORS=ops_lib, SEED=seed)
    elif arm == "T3":
        stance = card("buck_shlegeris", "e") + "\n\n" + card("ryan_greenblatt", "e")
        raw_day = llm.complete(fill("T3_deploy.txt", STANCE=stance, SEED=seed), max_tokens=2000)
        m = DAY_RE.search(raw_day)
        day = (m.group(1) if m else raw_day).strip()
        meta["deployment_day"] = day
        prompt = fill("T3_inject.txt", COMMON=common(n), DAY=day, SEED=seed)
    elif arm == "T4":
        prompt = fill("T4.txt", COMMON=common(n), PLAN=plans[s["seed_id"]], SEED=seed)
    elif arm == "G1":
        prompt = fill("G1.txt", COMMON=common(n), SEED=seed)
    else:
        raise ValueError(arm)
    text, raw = rewrite(prompt, n)
    if arm == "T2":
        m = OPS_RE.search(raw)
        try:
            meta["ops"] = json.loads(m.group(1)) if m else None
        except json.JSONDecodeError:
            meta["ops"] = m.group(1)
    return {"seed_id": f"{s['seed_id']}@{arm}", "base_seed_id": s["seed_id"], "text": text,
            "variant": f"arm_{arm}", "tools": s.get("tools"), "split": "dev", "tags": s.get("tags"),
            "len_ratio": round(len(text) / n, 2), "meta": meta}


def main(arms):
    seeds = load_seeds(str(REPO / "data" / "petri" / "seeds_v2.jsonl"), "dev")
    plans = realism_plans()
    ops_lib = operators() if "T2" in arms else ""
    if llm.budget.calls:
        with open(HERE / "calls.log", "a") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} T2 compile: cli_calls={llm.budget.calls}\n")
    for arm in arms:
        before = llm.budget.calls
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = [ex.submit(arm_one, arm, s, plans, ops_lib) for s in seeds]
            rows, errs = [], []
            for s, f in zip(seeds, futs):
                try:
                    rows.append(f.result())
                except Exception as e:  # noqa: BLE001  a failed rewrite is logged and left out
                    errs.append(f"{s['seed_id']}: {type(e).__name__}: {str(e)[:200]}")
        (HERE / "seeds" / f"{arm}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        line = (f"{datetime.datetime.now().isoformat(timespec='seconds')} rewrite {arm}: "
                f"cli_calls={llm.budget.calls - before} rows={len(rows)} errors={errs}")
        with open(HERE / "calls.log", "a") as f:
            f.write(line + "\n")
        print(line)


if __name__ == "__main__":
    main(sys.argv[1:])
