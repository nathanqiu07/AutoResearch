"""Owain's SynthesizeMe pipeline, re-pointed at Marius Hobbhahn, with every call on swe-2-medium via devin-cli.

The Owain modules (pairs_v2, pairs_v4, synthme/pairs.py, synthme/fit.py) are imported read-only and patched
here; nothing else differs. This dir mirrors experiments/taste_petri/'s layout so those modules' TP-relative
paths resolve inside it:
  profiles_contrastive/decisions_pre_t.jsonl   paper training decisions (pre-T)
  informal/                                    informal pre-T sources and decisions
  pairs_v4/                                    post-T test pair build (pairs_v2 sources + pairs_v4 stages)
  e2_v4/                                       the test sample and the M0s/NAME baseline predictions
"""
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TP = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(TP))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True  # importing the Owain modules must not write into their dirs

from autoresearch.llm import Budget, DevinCLILLM  # noqa: E402

SLUG, NAME, T = "marius_hobbhahn", "Marius Hobbhahn", "2026-01-01"
MODEL = "swe-2-medium"  # free on the Devin plan (user, 2026-11-15): every role, "sonnet" and "haiku" alike
WORKERS = 2
SLOTS = 2  # devin calls in flight across ALL processes: the account's request rate limit is shared with the session
UNCAPPED = 10 ** 9  # user: no call cap
TEST_DIR = os.path.join(HERE, "pairs_v4")
LOCK = threading.Lock()
_LLM = DevinCLILLM(MODEL, Budget(max_calls=UNCAPPED, max_seconds=1e9, max_cost_usd=1e9))

# A paper and its blog post or follow-up post are one work (split unit).
WORK_KEYS = [("in_context_scheming", ["ablations_for_frontier_models_are_capable"]),
             ("probabilistic_dangerous_capability_evals", ["analyzing_deepmind_s_probabilistic", "analyzing_probabilistic_methods"]),
             ("compute_trends", ["compute_trends_across", "compute_trends_comparison"]),
             ("scheming_safety_cases", ["toward_safety_cases_for_ai_scheming", "towards_evaluations_based_safety_cases"]),
             ("reflection_mechanisms", ["reflection_mechanisms_as_an_alignment_target"]),
             ("mech_interp_challenge", ["solving_the_mechanistic_interpretability_challenge"]),
             ("evaluation_awareness", ["do_models_know_when_they_are_being_evaluated", "large_language_models_often_know_when"]),
             ("happiness", ["what_makes_us_happy"]),
             ("productivity", ["guide_for_productivity"]),
             ("nuclear_energy", ["nuclear_energy"]),
             ("watcher", ["announcing_watcher_live", "watcher_an_mdm_for_ai_agents"])]
# Pre-T essays with no AI or research content, left out of the paper arm like the informal arm's off-topic items.
OFF_TOPIC_DOCS = ["how_to_sleep_better", "does_the_tax_revenue_from_cigarettes", "second_hand_clothes",
                  "i_have_accidentally_become_a_neoliberal", "nuclear_energy", "what_makes_us_happy", "efficient_speaking",
                  "guide_for_productivity", "the_case_for_genetic_enhancements", "our_mental_building_blocks"]
COINED = ["watcher"]  # post-T product name; check_pair already matches whole post-T titles


def work_of(doc):
    for work, keys in WORK_KEYS:
        if any(k in doc for k in keys):
            return work
    return re.sub(r"_[0-9a-f]{8}\.txt$", "", doc.replace("research__", ""))[:40].rstrip("_")


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


# ---------------------------------------------------------------- the one call wrapper

@contextlib.contextmanager
def _slot():
    """One of SLOTS cross-process slots (flock on cache/slot<i>), so parallel stages cannot exceed SLOTS calls."""
    os.makedirs(os.path.join(HERE, "cache"), exist_ok=True)
    while True:
        for i in range(SLOTS):
            f = open(os.path.join(HERE, "cache", f"slot{i}"), "w")
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                f.close()
                continue
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
                f.close()
            return
        time.sleep(0.5)


def _complete(prompt, system):
    """_LLM.complete in a slot; on the account's request rate limit, wait out the stated reset and retry."""
    for _ in range(30):
        try:
            with _slot():
                return _LLM.complete(prompt, system=system)
        except RuntimeError as e:
            m = re.search(r"reset in (\d+) seconds", str(e))
            if "rate limit" not in str(e):
                raise
            time.sleep((int(m.group(1)) if m else 60) + 5)
    raise RuntimeError("request rate limit: 30 waits without a successful call")


def call(model, tag, prompt, system="You are a careful research assistant."):
    """pairs_v2.call's contract (cached by prompt hash, logged, RuntimeError on failure) on devin-cli MODEL.
    `model` is the role the Owain code asked for ("sonnet"/"haiku"); it is logged and keyed, not used."""
    key = hashlib.sha256(json.dumps([MODEL, model, system, prompt]).encode()).hexdigest()[:32]
    cpath = os.path.join(HERE, "cache", key + ".json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f)["result"]
    log = os.path.join(HERE, "calls.log")

    def write(row):
        with LOCK, open(log, "a") as f:
            f.write(json.dumps(dict(t=time.strftime("%Y-%m-%dT%H:%M:%S"), model=model, backend=MODEL, tag=tag,
                                    key=key, **row)) + "\n")

    write({"chars": len(prompt), "status": "started"})
    t0 = time.time()
    try:
        out = _complete(prompt, system)
    except Exception as e:  # noqa: BLE001  (subprocess timeouts too: logged, then the caller's retry policy)
        write({"status": "error", "secs": round(time.time() - t0, 1), "out": str(e)[:200]})
        raise RuntimeError(f"devin CLI error ({tag}): {str(e)[:300]}") from e
    write({"status": "ok", "secs": round(time.time() - t0, 1), "out": out[:100]})
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    with open(cpath, "w") as f:
        json.dump({"model": model, "backend": MODEL, "tag": tag, "system": system, "prompt": prompt, "result": out}, f,
                  ensure_ascii=False)
    return out


# ---------------------------------------------------------------- loading the Owain modules, re-pointed

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _patch_v2(v2, here):
    v2.HERE, v2.SLUG, v2.T = here, SLUG, T
    v2.DATA = os.path.join(ROOT, "data", "researchers", SLUG)
    v2.CAPS = {"sonnet": UNCAPPED, "haiku": UNCAPPED}
    v2.WORKERS, v2.call, v2.work_of = WORKERS, call, work_of
    v2.EXTRA_DOCS, v2.COINED = [], COINED
    names_and_extra = v2.banned

    def banned():  # pairs_v2's name pattern has no closing word boundary, so "METR" matches every "metric"
        names, extra = names_and_extra()
        return names, re.compile(extra.pattern.replace("|METR|", "|METR\\b|"), extra.flags)

    v2.banned = banned


def _patch_v4(v4):  # v4.v2 is patched by the caller
    v4.V2_DIR, v4.call = TEST_DIR, call
    v4.CAPS = {"build": UNCAPPED, "gate": UNCAPPED}
    v4.PLAIN_TERMS = []  # Owain's two coined topic names
    v4.QUOTES = [d["quote"] for d in v4.sources()]


def test_pipeline():
    """pairs_v4/build.py (and its pairs_v2) writing into ./pairs_v4."""
    v4 = _load("hob_pairs_v4", os.path.join(TP, "pairs_v4", "build.py"))
    _patch_v2(v4.v2, TEST_DIR)
    _patch_v4(v4)
    return v4


def synthme_pairs():
    """synthme/pairs.py writing into this dir and reading this dir's decisions_pre_t / informal."""
    P = _load("hob_synthme_pairs", os.path.join(TP, "synthme", "pairs.py"))
    P.HERE = P.TP = HERE
    _patch_v2(P.v2, HERE)
    _patch_v4(P.v4)
    P.call, P.work_of = call, work_of
    P.BUILD_CAP = {"paper": UNCAPPED, "informal": UNCAPPED}
    P.informal_drop = lambda r: "in_paper_set" if r.get("in_paper_set") else "off_topic" if r.get("off_topic") else None
    return P


def synthme_fit():
    """synthme/fit.py on this dir's pairs; M0s and NAME are run here (no cached e2_v4 arms for him)."""
    P = synthme_pairs()
    sys.modules["pairs"] = P
    F = _load("hob_synthme_fit", os.path.join(TP, "synthme", "fit.py"))
    F.WORKERS, F.CACHED = WORKERS, ["M0s", "NAME"]
    test_model = F.test_model

    def baseline_or(arm):
        if arm in ("M0s", "NAME"):
            persona = "" if arm == "M0s" else f"The researcher is {NAME}."
            return F.Fixed(F.llm("test:" + arm), persona, cache_dir=os.path.join(HERE, "cache", "test_" + arm),
                           max_calls=400)
        return test_model(arm)

    F.test_model = baseline_or
    return F
