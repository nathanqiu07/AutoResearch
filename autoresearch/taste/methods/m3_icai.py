"""ICAI-inspired proposal, lexical clustering, and history reconstruction ranking."""
from ..usermodel import UserModel
from .common import accuracy, bounded_float, bounded_int, cluster_principles, example, selected_history


class InverseConstitutional(UserModel):
    method_id = "m3"
    prompt_version = "icai-bounded-v2"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.get("full_history"):
            self.prompt_version = type(self).prompt_version + "-paper-stages-v1"

    def fit(self, history, val):
        super().fit(history, val)
        if self.config.get("full_history"):
            from .full_history import fit_full
            self.prompt_version = type(self).prompt_version + "-paper-stages-v1"
            self._artifacts.metadata["prompt_version"] = self.prompt_version
            return fit_full(self, history, val)
        rows = selected_history(self, history)
        limit = bounded_int(self.config, "max_principles", 5)
        per_pair = bounded_int(self.config, "principles_per_pair", 2, minimum=1, maximum=5)
        threshold = bounded_float(self.config, "cluster_threshold", .75, minimum=.01)
        proposal_prompt = (
            'Propose at most %s preference principles explaining this choice. Return '
            '{"principles": ["concise principle, at most 600 characters"]}. Each is a '
            'tentative explanation: preserve relevant conditions, consider other explanations, '
            'and do not treat the selected response as factual truth or infer a universal '
            'personality trait from one choice.' % per_pair)
        meta = self._artifacts.metadata
        meta.update(source="https://github.com/rdnfn/icai",
                    adaptation="Bounded per-pair proposals; TF-IDF complete-link lexical clusters with medoids; "
                               "top-n in-sample reconstruction, not a reproduction of ICAI.",
                    verification_status="in_sample_reconstruction_only", selected_history_ids=[c.identity for c in rows],
                    extraction_prompts={"proposal": proposal_prompt}, principle_evidence=[],
                    selection_uses="history_only_no_validation_labels",
                    search_caps={"history": self.config.get("max_history", 5), "principles": limit,
                                 "principles_per_pair": per_pair}, cluster_threshold=threshold)
        proposals, provenance = [], []
        if not rows or not limit:
            meta.update(principle_proposals=[], clusters=[], reconstruction_scores=[])
            return
        for row in rows:
            result = self._json(proposal_prompt, {"choice": example(row)})
            values = result.get("principles")
            if (not isinstance(values, list) or not values or len(values) > per_pair or
                    any(not isinstance(v, str) or not v.strip() or len(v) > 600 for v in values)):
                raise ValueError("invalid proposed principles")
            for value in values:
                proposals.append(value.strip())
                provenance.append({"history_id": row.identity, "principle": value.strip()})
        clusters = cluster_principles(proposals, threshold)
        scored = []
        for cluster in clusters:
            principle = cluster["representative"]
            score = accuracy(rows, lambda context, options:
                             self._predict_with(context, options, principles=[principle]))
            scored.append({"principle": principle, "accuracy": score, "support": len(cluster["members"]),
                           "representative_index": cluster["representative_index"]})
        scored.sort(key=lambda item: (-item["accuracy"], -item["support"], item["representative_index"]))
        self._artifacts.principles = [item["principle"] for item in scored[:limit]]
        by_representative = {cluster["representative_index"]: cluster for cluster in clusters}
        meta["principle_evidence"] = [
            {"principle": item["principle"],
             "history_ids": sorted({provenance[index]["history_id"] for index in
                                    by_representative[item["representative_index"]]["members"]}),
             "status": "proposal_sources_not_independent_confirmation"}
            for item in scored[:limit]]
        meta.update(principle_proposals=provenance, clusters=clusters, reconstruction_scores=scored)
