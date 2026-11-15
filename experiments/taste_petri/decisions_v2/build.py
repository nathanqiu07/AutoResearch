"""Time-split research-decision data for four more public-track researchers (Steinhardt, Carlini,
Barnes, Marks), built from their dated corpora without touching data/.

    python3 experiments/taste_petri/decisions_v2/build.py select    # docs.json: picks + cutoff stats
    python3 experiments/taste_petri/decisions_v2/build.py extract   # one sonnet call per doc (cached)
    python3 experiments/taste_petri/decisions_v2/build.py assemble  # <slug>/decisions.jsonl, all.jsonl

Every real `claude -p --model sonnet` call is logged to calls.log and cached in cache/ by prompt hash;
the cap counts started calls in calls.log, so reruns cost nothing.
"""
import concurrent.futures
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
from autoresearch.llm import extract_json
from autoresearch.taste.timesplit import (
    _FIELDS,
    front_matter,
    normalize_for_quote,
    quote_in_text,
    read_doc,
)

CAP, WORKERS, MAX_CHARS = 72, 4, 160_000
LOCK = threading.Lock()

# Cutoff T: post-T means published on or after T. Chosen so >=30% of relevant docs are post-T.
CUTOFF = {"jacob_steinhardt": "2024-09-01", "nicholas_carlini": "2024-05-01",
          "elizabeth_barnes": "2023-07-01", "samuel_marks": "2025-09-01"}
# Relevant = dated, not middle author, no Hobbhahn in the author list, >=5k chars, and not off-topic
# hobby/personal writing (these substrings of file names).
OFF_TOPIC = {
    "nicholas_carlini": ["game_of_life", "doom_clone", "chess", "cpu_on_the", "hard_drive", "chatgpt_clone",
                         "minihdl", "intel_4004", "write_my_website", "career_update", "complete_list_of_all",
                         "plagarism", "how_i_use_ai"],
    "samuel_marks": ["mrna", "g_del_escher", "don_t_look_up", "prismatic", "agisf", "haist"],
    "jacob_steinhardt": ["principles_for_productive_group"],
    "elizabeth_barnes": ["is_hiring", "send_us_example", "managing_risks_of_our_own"],
}
# Hand-picked from the relevant docs, weighted to evals, auditing, robustness, alignment experiments
# and forecasting. Each entry is a unique file-name substring.
PICKS = {
    "jacob_steinhardt": [
        "certified_defenses_for_data_poisoning", "troubling_trends", "measuring_massive_multitask",
        "what_will_gpt_2030", "capturing_failures_of_large", "discovering_latent_knowledge",
        "automatically_auditing_large", "ai_forecasting_two_years", "jailbroken_how_does",
        "approaching_human_level_forecasting",
        "eliciting_language_model_behaviors_with_investig", "latentqa", "automatically_jailbreaking_frontier",
        "predictive_concept_decoders_training", "oversight_assistants", "foundation_models_for_oversight",
        "some_focus_areas_for_embedded_evaluations"],
    "nicholas_carlini": [
        "towards_evaluating_the_robustness", "adversarial_examples_are_not_easily_detected", "secret_sharer",
        "advice_on_evaluating_adversarial", "on_evaluating_adversarial_robustness",
        "extracting_training_data_from_large", "poisoning_web_scale", "are_aligned_neural_networks",
        "my_research_idea_logfile", "my_benchmark_for_large",
        "cutting_through_buggy", "why_i_attack", "ai_forecasting_retrospective", "autoadvexbench",
        "llms_unlock_new_paths", "detecting_adversarial_fine_tuning", "impossiblebench",
        "how_to_win_a_best_paper"],
    "elizabeth_barnes": [
        "writeup_progress_on_ai_safety_via_debate", "debate_update_obfuscated", "imitative_generalisation_aka",
        "call_for_research_on_evaluating", "more_detailed_proposal_for_measuring", "a_very_crude_deception",
        "risks_from_ai_persuasion", "help_arc_evaluate", "more_information_about_the_dangerous",
        "arc_evals_new_report", "bounty_diverse_hard_tasks", "clarifying_metr_s_auditing",
        "34_ai_evaluations_with_beth", "re_bench_evaluating", "hcast_human_calibrated", "217_beth_barnes",
        "thread_by_bethmaybarnes"],
    "samuel_marks": [
        "caution_when_interpreting_deepmind", "crosspost_acx_2022", "the_geometry_of_truth",
        "what_s_up_with_llms_representing_xors", "sparse_feature_circuits", "discriminating_behaviorally",
        "auditing_language_models_for_hidden", "downstream_applications_as_validation",
        "building_and_evaluating_alignment_auditing", "towards_alignment_auditing_as",
        "eliciting_secret_knowledge", "inoculation_prompting_instructing_llms", "liars_bench",
        "activation_oracles_training", "the_persona_selection_model", "introspection_adapters",
        "would_this_change_your_answer"],
}
# Docs of one researcher that are the same work (paper + blog post). None of the picks pair up today;
# a doc not listed here is its own work.
SAME_WORK = {}

PROMPT = """You extract research DECISIONS from one document by {name}. A decision is a choice the \
authors made about how to do research, where another choice was possible. Decision points: D1 which \
experiment or hypothesis to pursue; D2 what evidence to collect (for example asking the model directly \
vs using probes); D3 whether to accept a result; D4 whether to continue or drop a line of work; D5 how \
to interpret an ambiguous result; D6 how strongly to state a claim.

Return 4-10 decisions, preferring ones about research methodology (evaluation design, auditing, \
robustness checks, experimental controls, forecasting) over routine implementation details. Only \
include decisions the document itself describes. For each give:
- point: one of D1-D6
- problem: the research problem or question faced, stated neutrally (1 sentence)
- did: what the authors chose to do (1 sentence)
- alternatives_named: a JSON list of strings, the alternatives the text itself names or rejects ([] if none)
- stated_reason: the reason the text gives ("" if none)
- quote: a VERBATIM passage from the document, 15-60 words, copied character for character, that shows \
the decision. Do not paraphrase, merge sentences, or use ellipses.

Return only JSON: {{"decisions": [{{"point": ..., "problem": ..., "did": ..., "alternatives_named": [...], \
"stated_reason": ..., "quote": ...}}]}}

DOCUMENT ({title}, {date}):
"""
NAMES = {"jacob_steinhardt": "Jacob Steinhardt", "nicholas_carlini": "Nicholas Carlini",
         "elizabeth_barnes": "Elizabeth Barnes", "samuel_marks": "Samuel Marks"}
REFS = re.compile(r"^\s*#{0,6}\s*\**\s*(\d+\.?\s*)?(references|bibliography)\s*\**\s*$", re.IGNORECASE | re.MULTILINE)


def p(*parts):
    return os.path.join(HERE, *parts)


def corpus(slug):
    return sorted(glob.glob(os.path.join(ROOT, "data", "researchers", slug, "corpus", "*.txt")))


def relevant(slug, path):
    fm = front_matter(path)
    date, text = read_doc(path)
    name = os.path.basename(path)
    return (date is not None and fm.get("author_position") != "middle"
            and "hobbhahn" not in fm.get("authors", "").lower() and len(text) >= 5000
            and not any(k in name for k in OFF_TOPIC[slug]))


def strip_refs(text):
    """Drop each References/Bibliography section, up to the next markdown heading (appendices follow
    the references in arXiv HTML)."""
    for m in reversed(list(REFS.finditer(text))):
        nxt = re.search(r"^#", text[m.end():], re.MULTILINE)
        text = text[:m.start()] + (text[m.end() + nxt.start():] if nxt else "")
    return text


def select():
    out = {}
    for slug, picks in PICKS.items():
        paths = [x for x in corpus(slug) if relevant(slug, x)]
        dates = [str(read_doc(x)[0]) for x in paths]
        t = CUTOFF[slug]
        post = sum(d >= t for d in dates)
        docs = []
        for key in picks:
            hits = [x for x in paths if key in os.path.basename(x)]
            assert len(hits) == 1, (slug, key, hits)
            fm = front_matter(hits[0])
            docs.append({"doc": os.path.basename(hits[0]), "date": fm["publishedDate"][:10], "title": fm.get("title", ""),
                         "url": fm.get("url", ""), "author_position": fm.get("author_position"), "kind": fm.get("kind")})
        assert all("hobbhahn" not in front_matter(os.path.join(os.path.dirname(paths[0]), d["doc"])).get("authors", "").lower()
                   for d in docs)
        pre_n = sum(d["date"] < t for d in docs)
        assert pre_n <= 10 and len(docs) - pre_n <= 8, (slug, pre_n)
        out[slug] = {"cutoff": t, "relevant": len(paths), "relevant_post": post,
                     "post_frac": round(post / len(paths), 3), "docs": docs}
        print(slug, t, f"relevant {len(paths)}, post {post} ({post / len(paths):.0%}); picked pre {pre_n} post {len(docs) - pre_n}")
    assert sum(len(v["docs"]) for v in out.values()) <= CAP
    with open(p("docs.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)


def started_calls():
    if not os.path.exists(p("calls.log")):
        return 0
    with open(p("calls.log")) as f:
        return sum('"status": "started"' in line for line in f)


def sonnet(prompt, tag):
    key = hashlib.sha256(json.dumps(["sonnet", prompt]).encode()).hexdigest()[:32]
    cpath = p("cache", key + ".json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f)["result"]
    with LOCK:
        n = started_calls()
        if n >= CAP:
            raise RuntimeError(f"call cap {CAP} reached")
        with open(p("calls.log"), "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": n + 1, "tag": tag, "key": key,
                                "chars": len(prompt), "status": "started"}) + "\n")
    cmd = ["claude", "-p", "--model", "sonnet", "--output-format", "json", "--tools", "", "--strict-mcp-config",
           "--no-session-persistence", "--setting-sources", "", "--system-prompt",
           "You extract structured data from documents and answer with JSON only."]
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="dv2_cli_") as cwd:
        proc = subprocess.run(cmd, check=False, input=prompt, capture_output=True, text=True, timeout=900, cwd=cwd)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {"is_error": True, "result": (proc.stderr or proc.stdout)[:300]}
    ok = proc.returncode == 0 and not data.get("is_error")
    with LOCK, open(p("calls.log"), "a") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "tag": tag, "key": key,
                            "status": "ok" if ok else "error", "secs": round(time.time() - t0, 1),
                            "cost_usd": data.get("total_cost_usd"), "out": str(data.get("result"))[:120]}) + "\n")
    if not ok:
        raise RuntimeError(f"claude CLI error on {tag}: {str(data.get('result'))[:300]}")
    with open(cpath, "w") as f:
        json.dump({"tag": tag, "prompt_chars": len(prompt), "result": data["result"]}, f, ensure_ascii=False)
    return data["result"]


def doc_prompt(slug, d):
    _, text = read_doc(os.path.join(ROOT, "data", "researchers", slug, "corpus", d["doc"]))
    return PROMPT.format(name=NAMES[slug], title=d["title"], date=d["date"]) + strip_refs(text)[:MAX_CHARS]


def extract():
    with open(p("docs.json")) as f:
        sel = json.load(f)
    os.makedirs(p("cache"), exist_ok=True)
    jobs = [(slug, d) for slug, v in sel.items() for d in v["docs"]]
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        futs = {pool.submit(sonnet, doc_prompt(slug, d), f"{slug}/{d['doc'][:60]}"): d["doc"] for slug, d in jobs}
        for fu in concurrent.futures.as_completed(futs):
            try:
                fu.result()
                print("ok", futs[fu][:70])
            except (RuntimeError, subprocess.TimeoutExpired) as e:  # a rerun retries uncached docs
                print("FAIL", futs[fu][:70], e)
    print("started calls so far:", started_calls())


def clean(d):
    d = {k: d.get(k) for k in _FIELDS}
    alts = d["alternatives_named"]
    d["alternatives_named"] = ([] if alts in (None, "", "null", "none", "None")
                               else [alts] if isinstance(alts, str) else [str(a) for a in alts if a])
    d["stated_reason"] = "" if d["stated_reason"] in (None, "null") else str(d["stated_reason"])
    return d


def assemble():
    with open(p("docs.json")) as f:
        sel = json.load(f)
    everything, stats = [], {}
    for slug, v in sel.items():
        t, rows = v["cutoff"], []
        s = {"docs": len(v["docs"]), "docs_extracted": 0, "raw": 0, "kept": 0, "drop_quote": 0, "drop_did": 0,
             "drop_hobbhahn": 0, "drop_dup": 0, "drop_quote_len": 0}
        for d in v["docs"]:
            prompt = doc_prompt(slug, d)
            cpath = p("cache", hashlib.sha256(json.dumps(["sonnet", prompt]).encode()).hexdigest()[:32] + ".json")
            if not os.path.exists(cpath):
                continue
            with open(cpath) as f:
                out = extract_json(json.load(f)["result"])
            s["docs_extracted"] += 1
            _, text = read_doc(os.path.join(ROOT, "data", "researchers", slug, "corpus", d["doc"]))
            seen = set()
            for raw in (out or {}).get("decisions") or []:
                if not isinstance(raw, dict):
                    continue
                s["raw"] += 1
                dec = clean(raw)
                quote = str(dec["quote"] or "")
                if not str(dec["did"] or "").strip() or str(dec["did"]).strip().lower() == "null":
                    s["drop_did"] += 1
                elif "hobbhahn" in json.dumps(dec).lower():
                    s["drop_hobbhahn"] += 1
                elif not quote_in_text(quote, text):
                    s["drop_quote"] += 1
                elif not 15 <= len(quote.split()) <= 60:
                    s["drop_quote_len"] += 1
                elif normalize_for_quote(quote) in seen:
                    s["drop_dup"] += 1
                else:
                    seen.add(normalize_for_quote(quote))
                    rows.append(dict(dec, researcher=slug, doc=d["doc"], url=d["url"], title=d["title"], date=d["date"],
                                     split="post" if d["date"] >= t else "pre", cutoff=t,
                                     author_position=d["author_position"], kind=d["kind"],
                                     work_id=f"{slug}:{SAME_WORK.get(d['doc'], d['doc'][:-4])}",
                                     decision_id=hashlib.sha256((d["doc"] + normalize_for_quote(quote)).encode()).hexdigest()[:12]))
        s["kept"] = len(rows)
        s["kept_pre"] = sum(r["split"] == "pre" for r in rows)
        s["kept_post"] = sum(r["split"] == "post" for r in rows)
        s["docs_pre"] = sum(d["date"] < t for d in v["docs"])
        s["docs_post"] = s["docs"] - s["docs_pre"]
        s["works_post"] = len({r["work_id"] for r in rows if r["split"] == "post"})
        s.update(cutoff=t, relevant=v["relevant"], relevant_post=v["relevant_post"], post_frac=v["post_frac"])
        stats[slug] = s
        os.makedirs(p(slug), exist_ok=True)
        with open(p(slug, "decisions.jsonl"), "w") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        everything += rows
    with open(p("all.jsonl"), "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in everything)
    with open(p("stats.json"), "w") as f:
        json.dump(stats, f, indent=1)
    print(json.dumps(stats, indent=1))


def readme():
    with open(p("stats.json")) as f:
        stats = json.load(f)
    with open(p("all.jsonl")) as f:
        rows = [json.loads(line) for line in f]
    calls = started_calls()
    lines = ["# decisions_v2: time-split research decisions for four public-track researchers", "",
             ("Built by `build.py` (select -> extract -> assemble -> readme) from `data/researchers/<slug>/corpus/` "
              "without writing to data/. One `claude -p --model sonnet` call per doc (refs sections stripped, "
              f"capped at {MAX_CHARS // 1000}k chars); {calls} real calls in `calls.log` (cap {CAP}), cached in `cache/`."),
             "", ("Relevant docs: dated, the researcher not a middle author, no Hobbhahn in the author list, >=5k chars, "
             "off-topic hobby writing excluded (`OFF_TOPIC`). Post-T means published on or after T. Picks are hand-chosen "
             "(`PICKS`), weighted to evals, auditing, robustness, alignment experiments and forecasting."), "",
             ("Each kept decision: the timesplit fields (point, problem, did, alternatives_named as a list, stated_reason, "
             "quote) plus researcher, doc, url, title, date, split, cutoff, author_position, kind, work_id, decision_id. "
             "Dropped: `did` empty/null, any field mentioning Hobbhahn, quote failing `timesplit.quote_in_text` "
             "against the doc, quote outside 15-60 words, duplicate quote within a doc."), "",
             ("| researcher | T | relevant docs (post-T) | docs pre/post | raw | kept | kept pre/post | dropped: quote not found / quote length / did empty / Hobbhahn / dup | works post-T |"),
             "|---|---|---|---|---|---|---|---|---|"]
    for slug, s in stats.items():
        lines.append(f"| {slug} | {s['cutoff']} | {s['relevant']} ({s['relevant_post']}, {s['post_frac']:.0%}) | "
                     f"{s['docs_pre']}/{s['docs_post']} | {s['raw']} | {s['kept']} | {s['kept_pre']}/{s['kept_post']} | "
                     f"{s['drop_quote']} / {s['drop_quote_len']} / {s['drop_did']} / {s['drop_hobbhahn']} / {s['drop_dup']} | "
                     f"{s['works_post']} |")
    lines += ["", "Every picked doc is its own work (no paper + blog-post pair was picked), so works = docs with kept decisions.", ""]
    for slug in stats:
        lines += [f"## Examples: {NAMES[slug]}", ""]
        mine = [r for r in rows if r["researcher"] == slug]
        for r in (mine[::max(1, len(mine) // 3)])[:3]:
            lines += [f"- **{r['point']}** ({r['date']}, {r['split']}-T, {r['author_position']}) *{r['title']}*",
                      f"  - problem: {r['problem']}", f"  - did: {r['did']}",
                      f"  - alternatives: {'; '.join(r['alternatives_named']) or '(none named)'}",
                      f"  - reason: {r['stated_reason'] or '(none stated)'}", f"  - quote: \"{r['quote']}\"", ""]
    with open(p("README.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    {"select": select, "extract": extract, "assemble": assemble, "readme": readme}[sys.argv[1]]()
