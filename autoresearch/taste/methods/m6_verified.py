"""Validation-based leave-one-out removal of strictly harmful hybrid components."""
from .common import accuracy, bounded_int, remove_harmful
from .m5_hybrid import Hybrid


class VerifiedHybrid(Hybrid):
    method_id = "m6"

    def fit(self, history, val):
        max_lines = bounded_int(self.config, "max_persona_lines", 5, minimum=1)
        super().fit(history, val)
        meta = self._artifacts.metadata
        meta.update(adaptation=meta["adaptation"] + " Iterative validation leave-one-out filter.",
                    filter_tie_policy="keep", filter_trace=[],
                    filter_claim="Removes observed strict harms; survivors need not independently improve accuracy.")
        if not val:
            meta["verification_status"] = "unverified_hybrid_fallback_no_validation"
            return
        components = [("principle", text) for text in self._artifacts.principles]
        lines = [line.strip() for line in self._artifacts.persona.splitlines() if line.strip()]
        # Bound filter calls without dropping arbitrary user-model text. Long
        # personas are tested as contiguous line groups, recorded as an adaptation.
        width = max(1, (len(lines) + max_lines - 1) // max_lines)
        components += [("persona", "\n".join(lines[i:i + width])) for i in range(0, len(lines), width)]
        meta["persona_line_grouping"] = {"original_lines": len(lines), "maximum_components": max_lines,
                                          "lines_per_component": width}

        def score(items):
            principles = [text for kind, text in items if kind == "principle"]
            persona = "\n".join(text for kind, text in items if kind == "persona")
            return accuracy(val, lambda context, options:
                            self._predict_components(context, options, principles, persona))

        kept, trace = remove_harmful(components, score)
        self._artifacts.principles = [text for kind, text in kept if kind == "principle"]
        self._artifacts.persona = "\n".join(text for kind, text in kept if kind == "persona")
        meta.update(filter_components=components, filter_trace=trace,
                    verification_status="filtered_on_validation_not_independently_verified")
