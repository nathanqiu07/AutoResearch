"""Deterministic fixture backend for testing the user-model plumbing, never accuracy.

This is deliberately a trivial response-length world. It does not emulate an LLM,
infer real preferences, or provide empirical evidence about PRISM participants.
"""
import json

from ..llm import Budget, LLM


def fixture_records():
    """Six synthetic pairs in three disjoint conversation partitions.

    The fixture person always chooses the longer response; the generic fixture
    judge prefers shorter ones. The planted rule exercises M2/M3 selection and
    must not be interpreted as a result about public participants.
    """
    from .prefdata import PreferenceRecord
    from .usermodel import Choice

    rows = []
    for split in ("history", "val", "test"):
        for i in range(2):
            short = "Brief fixture option %s %s." % (split, i)
            long = short + " This longer synthetic explanation is preferred by the planted fixture person."
            a, b, chosen = (short, long, "b") if i == 0 else (long, short, "a")
            eid = "fixture-%s-%s" % (split, i)
            rows.append(PreferenceRecord(
                Choice("prism:offline-fixture", "SYNTHETIC PLUMBING EXAMPLE: " + eid,
                       a, b, chosen, source="synthetic_fixture_not_prism",
                       example_id=eid, group_id="fixture-conversation-" + split),
                "prism", "dev", split, "train"))
    return rows


class OfflineTasteLLM(LLM):
    name = "offline-taste-fixture"

    def __init__(self, model="fixture-v1", budget=None):
        if model != "fixture-v1":
            raise ValueError("offline taste backend supports only fixture-v1")
        super().__init__(budget or Budget())
        self.model = model

    @staticmethod
    def _direction(choice):
        picked = choice[choice["chosen"] + "_text"]
        other = choice[("b" if choice["chosen"] == "a" else "a") + "_text"]
        return "longer" if len(picked) > len(other) else "shorter"

    def complete(self, prompt, system="", max_tokens=2048, temperature=0.0):
        if self.budget.exhausted():
            raise RuntimeError("offline fixture call budget exhausted")
        instruction, encoded = prompt.split("\nINPUT_JSON:\n", 1)
        payload = json.loads(encoded)
        if instruction.startswith("Explain why"):
            direction = self._direction(payload["choice"])
            result = {"hypothesis": "OFFLINE FIXTURE ONLY: prefer the %s response." % direction}
        elif instruction.startswith("Propose") and "principles" in instruction:
            direction = self._direction(payload["choice"])
            result = {"principles": ["OFFLINE FIXTURE ONLY: prefer the %s response." % direction]}
        elif instruction.startswith("Write a short persona"):
            result = {"persona": "\n".join(payload["hypotheses"])}
        elif "options" in payload:
            options = payload["options"]
            if len(options) < 2:
                raise ValueError("fixture prediction needs at least two options")
            personal = " ".join(payload.get("principles", [])) + " " + payload.get("persona", "")
            directions = [self._direction(c) for c in payload.get("past_choices", [])]
            if "longer" in personal or "shorter" in personal:
                longer = personal.count("longer") > personal.count("shorter")
            else:
                longer = directions.count("longer") > directions.count("shorter")
            best = (max if longer else min)(range(len(options)), key=lambda i: len(options[i]))
            weights = [3.0 if i == best else 1.0 for i in range(len(options))]
            result = {"probabilities": [w / sum(weights) for w in weights],
                      "rationale": "OFFLINE FIXTURE ONLY: deterministic response-length rule; "
                                   "not a real preference prediction."}
        else:
            raise ValueError("unsupported offline fixture request; only M0-M3 are supported")
        text = json.dumps(result, ensure_ascii=False)
        self.budget.charge(max(1, len(system + prompt) // 4), max(1, len(text) // 4))
        return text

    def cost_summary(self):
        return {"spent_usd": 0.0, "reserved_usd": 0.0,
                "cost_basis": "offline_fixture_no_api_calls_tokens_are_character_estimates",
                "evidence_status": "simulated_plumbing_only"}
