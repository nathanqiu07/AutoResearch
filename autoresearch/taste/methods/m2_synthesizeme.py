"""Bounded SynthesizeMe adaptation: validate hypotheses, persona, demonstrations."""
from ..usermodel import UserModel
from .common import accuracy, bounded_int, example, forward_select, selected_history, text_field


class SynthesizeMe(UserModel):
    method_id = "m2"
    prompt_version = "synthesizeme-bounded-v2"

    def fit(self, history, val):
        super().fit(history, val)
        rows = selected_history(self, history)
        max_hypotheses = bounded_int(self.config, "max_hypotheses", 5)
        max_examples = bounded_int(self.config, "max_exemplars", 3)
        max_chars = bounded_int(self.config, "max_persona_chars", 1600, minimum=1, maximum=10000)
        hypothesis_prompt = (
            'Explain why this user chose this reply. Return {"hypothesis": "one concise '
            'preference hypothesis, at most 600 characters"}. Treat the reason as a tentative '
            'inference, not a known motive. Prefer a conditional preference; do not equate '
            'the selected response with factual truth or invent a universal personality trait.')
        persona_prompt = (
            'Write a short persona using only these hypotheses. Return '
            '{"persona": "persona text"}. Use at most %s characters. Preserve conditions '
            'and uncertainty; do not invent new preferences.' % max_chars)
        meta = self._artifacts.metadata
        meta.update(source="https://github.com/SALT-NLP/SynthesizeMe",
                    adaptation="Bounded per-pair hypotheses and greedy validation search; no DSPy random search.",
                    selected_history_ids=[c.identity for c in rows], hypothesis_trace=[], exemplar_trace=[],
                    extraction_prompts={"hypothesis": hypothesis_prompt, "persona": persona_prompt},
                    principle_evidence=[],
                    prediction_components=["persona", "selected_history_examples"],
                    proposer_principles_status="validation_selected_hypotheses_not_research_validated",
                    search_caps={"history": self.config.get("max_history", 5), "hypotheses": max_hypotheses,
                                 "exemplars": max_examples, "persona_chars": max_chars})
        if not rows or not val:
            self._artifacts.exemplars = [example(c) for c in rows[:max_examples]]
            meta["verification_status"] = "unverified_raw_history_fallback"
            return
        hypotheses, proposals = [], []
        for row in rows:
            result = self._json(hypothesis_prompt, {"choice": example(row)})
            hypothesis = text_field(result, "hypothesis", 600)
            proposals.append({"history_id": row.identity, "hypothesis": hypothesis})
            if hypothesis not in hypotheses:
                hypotheses.append(hypothesis)
        score_hypotheses = lambda items: accuracy(val, lambda context, options:
                                                 self._predict_with(context, options, principles=items))
        kept, trace = forward_select(hypotheses, score_hypotheses, max_hypotheses)
        meta.update(hypothesis_proposals=proposals, retained_hypotheses=kept, hypothesis_trace=trace)
        # The research proposer reads artifacts.principles, not persona. Export
        # selected hypotheses there, but keep the tested prediction path below.
        self._artifacts.principles = list(kept)
        meta["principle_evidence"] = [
            {"principle": hypothesis,
             "history_ids": [p["history_id"] for p in proposals if p["hypothesis"] == hypothesis],
             "status": "hypothesis_selected_on_validation"}
            for hypothesis in kept]
        persona = ""
        if kept:
            result = self._json(persona_prompt, {"hypotheses": kept})
            persona = text_field(result, "persona", max_chars)
            baseline = score_hypotheses([])
            candidate = accuracy(val, lambda context, options:
                                 self._predict_with(context, options, persona=persona))
            # Retain whole hypotheses only; cutting a sentence can reverse its meaning.
            fallback_lines = []
            for hypothesis in kept:
                if len("\n".join(fallback_lines + [hypothesis])) <= max_chars:
                    fallback_lines.append(hypothesis)
            fallback = "\n".join(fallback_lines)
            fallback_score = accuracy(val, lambda context, options:
                                      self._predict_with(context, options, persona=fallback))
            meta["persona_validation"] = {"baseline": baseline, "synthesized": candidate,
                                           "hypothesis_text": fallback_score,
                                           "fallback_hypotheses": len(fallback_lines)}
            if candidate < max(baseline, fallback_score):
                persona = fallback if fallback_score >= baseline else ""
                meta["persona_validation"]["fallback_used"] = True
        self._artifacts.persona = persona
        candidates = [example(c) for c in rows]
        score_examples = lambda items: accuracy(val, lambda context, options:
                                               self._predict_with(context, options, persona=persona,
                                                                  exemplars=items))
        self._artifacts.exemplars, meta["exemplar_trace"] = forward_select(candidates, score_examples, max_examples)
        meta["verification_status"] = "selected_on_validation_not_independently_verified"

    def predict(self, context, options):
        # Do not silently add exported proposer rules to the persona/example
        # combination selected above: that would be a new, untested condition.
        return self._predict_with(context, options, persona=self._artifacts.persona,
                                  exemplars=self._artifacts.exemplars)
