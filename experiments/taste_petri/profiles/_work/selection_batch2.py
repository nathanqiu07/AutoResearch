"""Batch 2 (Marks, Barnes, Steinhardt): append <=15 picks per researcher to selection.json without touching the
existing 98 entries, so map_one.sh indices and the first five profiles stay valid. Re-running is a no-op.
Docs with Marius Hobbhahn in the authors line are dropped (he is a tester).
(selection.py is not imported: it rewrites selection.json at import time.)"""
import json, os, re, sys
ROOT = "/Users/ethancai/Projects/Ongoing/AutoResearch/data/researchers"
W = os.path.dirname(os.path.abspath(__file__))
PICK = {
 "samuel_marks": ["petri_an_open_source", "towards_alignment_auditing_as_a_numbers", "auditing_language_models_for_hidden",
   "building_and_evaluating_alignment_auditing", "downstream_applications_as_validation", "principles_for_picking_practical",
   "recommendations_for_technical_ai_safety", "auditbench_evaluating", "auditing_games_for_sandbagging",
   "steering_evaluation_aware", "the_persona_selection_model", "evaluating_honesty_and_lie_detection",
   "training_models_to_predict_and_explain", "modifying_llm_beliefs_with_synthetic", "discriminating_behaviorally_identical"],
 "elizabeth_barnes": ["217_beth_barnes", "34_ai_evaluations_with_beth", "arc_evals_new_report", "a_very_crude_deception_eval",
   "call_for_research_on_evaluating_alignment", "more_detailed_proposal_for_measuring", "more_information_about_the_dangerous",
   "clarifying_metr_s_auditing", "re_bench_evaluating", "hcast_human_calibrated", "measuring_ai_ability_to_complete",
   "thread_by_bethmaybarnes", "bounty_diverse_hard_tasks", "measuring_the_impact_of_early_2025", "managing_risks_of_our_own"],
 "jacob_steinhardt": ["user_awareness_in_frontier", "some_focus_areas_for_embedded", "introducing_docent",
   "eliciting_language_model_behaviors_with_investigat", "automatically_jailbreaking_frontier", "investigating_truthfulness_in_a_pre",
   "surfacing_pathological_behaviors", "oversight_assistants", "foundation_models_for_oversight",
   "building_technology_to_drive", "establishing_best_practices", "feedback_loops_with_language",
   "scalably_extracting_latent", "troubling_trends", "analyzing_long_agent_transcripts"],
}


def meta(path):
    head = open(path, errors="ignore").read(3000)
    m = {}
    for k in ("title", "publishedDate", "author_position", "kind", "url", "authors"):
        r = re.search(r"^%s: (.*)$" % k, head, re.M)
        m[k] = r.group(1).strip() if r else ""
    return m


sel = json.load(open(W + "/selection.json"))
have = {s["slug"] for s in sel}
for slug, keys in PICK.items():
    if slug in have:
        continue
    files = sorted(os.listdir(f"{ROOT}/{slug}/corpus"))
    for k in keys:
        hits = [f for f in files if k in f]
        if not hits:
            print("MISSING", slug, k, file=sys.stderr); continue
        p = f"{ROOT}/{slug}/corpus/{hits[0]}"
        m = meta(p)
        if "hobbhahn" in m.pop("authors").lower():
            print("DROP (Hobbhahn author)", hits[0], file=sys.stderr); continue
        sel.append(dict(slug=slug, file=hits[0], path=p, chars=os.path.getsize(p), **m))
json.dump(sel, open(W + "/selection.json", "w"), indent=1)
for i, o in enumerate(sel):
    if o["slug"] in PICK:
        print(i, o["slug"][:6], o["chars"], o["author_position"], o["kind"], o["publishedDate"], o["title"][:60])
