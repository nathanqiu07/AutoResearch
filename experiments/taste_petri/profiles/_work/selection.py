"""Pick the docs to map for each researcher: filename-substring keys, in priority order."""
import json, os, re, sys
ROOT = "/Users/ethancai/Projects/Ongoing/AutoResearch/data/researchers"
# Docs with Marius Hobbhahn as an author are excluded (he is a tester).
EXCLUDE = ["chain_of_thought_monitorability", "me_myself_and_ai", "towards_evaluations_based_safety"]
PICK = {
 "evan_hubinger": ["model_organisms_of_misalignment_the_case", "39_evan_hubinger_on_model_organisms",
   "when_can_we_trust_model_evaluations", "towards_understanding_based_safety", "sleeper_agents_training",
   "evan_hubinger_on_training_deceptive", "how_to_train_your_own_sleeper", "alignment_faking_in_large",
   "introducing_alignment_stress_testing", "uncovering_deceptive_tendencies", "sycophancy_to_subterfuge",
   "auditing_language_models_for_hidden", "building_and_evaluating_alignment_auditing", "agentic_misalignment",
   "natural_emergent_misalignment", "towards_training_time_mitigations", "pre_deployment_auditing_can_catch",
   "training_a_misaligned_reward_seeker", "alignment_remains_a_hard", "automating_subtle_emergent",
   "monitoring_for_deceptive_alignment", "bing_chat_is_blatantly", "how_likely_is_deceptive_alignment",
   "will_ai_tell_lies", "evhub_s_shortform", "catastrophic_sabotage_as_a_major"],
 "samuel_bowman": ["eight_things_to_know", "measuring_progress_on_scalable", "artificial_sandwiching",
   "the_checklist_what_succeeding", "putting_up_bumpers", "claude_finds_god", "findings_from_a_pilot_anthropic",
   "lessons_learned_from_the_first_misalignment", "auditbench_evaluating", "auditing_language_models_for_hidden",
   "building_and_evaluating_alignment_auditing", "automated_researchers_can_subtly", "what_will_it_take_to_fix_benchmarking",
   "dangers_of_underclaiming", "adversarially_constructed_evaluation", "annotation_artifacts_in_natural",
   "discovering_language_model_behaviors_with_model_written", "llm_evaluators_recognize", "towards_understanding_sycophancy",
   "a_small_negative_result_on_debate", "asking_crowdworkers_to_write", "adversarial_scalable_oversight",
   "language_models_learn_to_mislead", "alignment_faking_in_large"],
 "owain_evans": ["deluding_ais", "taken_out_of_context_on_measuring", "paper_on_measuring_situational",
   "conditional_misalignment_common", "conditional_misalignment_mitigations", "tell_me_about_yourself",
   "concept_poisoning", "emergent_misalignment_far_ai", "emergent_misalignment_narrow", "thought_crime",
   "backdoor_awareness", "how_to_catch_an_ai_liar", "three_half_baked", "value_leakage", "secret_loyalties",
   "training_with_conflicting_values", "some_background_reading", "ai_safety_research_project_ideas",
   "owain_evans_s_shortform", "school_of_reward_hacks", "out_of_context_reasoning_in_llms", "looking_inward"],
 "ryan_greenblatt": ["sonnet_4_5_s_eval_gaming_seriously_under", "will_alignment_faking_claude_accept",
   "prospects_for_studying_actual_schemers", "to_be_legible_evidence", "how_will_we_update_about_scheming",
   "notes_on_control_evaluations", "meta_level_adversarial", "catching_ais_red_handed", "towards_understanding_score_seeking",
   "believe_it_or_not", "iterated_development_and_study", "reducing_risk_from_scheming", "alignment_faking_in_large",
   "ai_control_improving_safety", "27_ai_control_with_buck", "ryan_greenblatt_s_shortform", "comments_current_ais_seem",
   "reward_hacking_without_egregious", "an_overview_of_control_measures", "inference_scaling_alignment_faking",
   "notes_on_countermeasures_for_exploration", "anthropic_repeatedly_accidentally"],
}
def meta(path):
    head = open(path, errors="ignore").read(3000)
    m = {}
    for k in ("title", "publishedDate", "author_position", "kind", "url"):
        r = re.search(r"^%s: (.*)$" % k, head, re.M)
        m[k] = r.group(1).strip() if r else ""
    return m
out = []
for slug, keys in PICK.items():
    files = sorted(os.listdir(f"{ROOT}/{slug}/corpus"))
    for k in keys:
        hits = [f for f in files if k in f and not any(e in f for e in EXCLUDE)]
        if not hits:
            print("MISSING", slug, k, file=sys.stderr); continue
        f = hits[0]
        p = f"{ROOT}/{slug}/corpus/{f}"
        m = meta(p)
        out.append(dict(slug=slug, file=f, path=p, chars=os.path.getsize(p), **m))
json.dump(out, open(os.path.join(os.path.dirname(__file__), "selection.json"), "w"), indent=1)
for o in out: print(o["slug"][:6], o["chars"], o["author_position"], o["kind"], o["publishedDate"], o["title"][:60])
