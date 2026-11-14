"""Combine the bounded M2/M3 artifacts and retrieve examples lexically."""
from ..usermodel import UserModel
from .common import bounded_int, example, fit_child, retrieve, selected_history
from .m2_synthesizeme import SynthesizeMe
from .m3_icai import InverseConstitutional


class Hybrid(UserModel):
    method_id = "m5"

    def fit(self, history, val):
        super().fit(history, val)
        count = bounded_int(self.config, "max_exemplars", 3)
        rows = selected_history(self, history)
        synthesized = fit_child(self, SynthesizeMe, rows, val)
        constitutional = fit_child(self, InverseConstitutional, rows, val)
        self._artifacts.persona = synthesized.persona
        self._artifacts.principles = constitutional.principles
        self._artifacts.exemplars = synthesized.exemplars[:count]
        self._artifacts.metadata.update(
            adaptation="M2 persona plus M3 principles with query-time TF-IDF history retrieval; proposed hybrid.",
            sources=["https://github.com/SALT-NLP/SynthesizeMe", "https://github.com/rdnfn/icai"],
            components={"m2": synthesized.metadata, "m3": constitutional.metadata},
            retrieval_pool=[example(row) for row in rows], retrieval_count=count,
            verification_status="hybrid_not_independently_verified")

    def _predict_components(self, context, options, principles, persona):
        meta = self._artifacts.metadata
        exemplars = retrieve(context, options, meta.get("retrieval_pool", self._artifacts.exemplars),
                             meta.get("retrieval_count", self.config.get("max_exemplars", 3)))
        return self._predict_with(context, options, principles=principles, persona=persona, exemplars=exemplars)

    def predict(self, context, options):
        return self._predict_components(context, options, self._artifacts.principles, self._artifacts.persona)
