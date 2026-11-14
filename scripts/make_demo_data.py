"""Generate demo researcher identities (corpus + structured choices).

Real use: scrape a real person with `python -m autoresearch scrape`, and add
choices.jsonl from their actual decisions (`python -m autoresearch label`).
These synthetic identities have known hidden weights, so taste-prediction
accuracy can be checked against ground truth."""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from autoresearch.taste.profile import FEATURES  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "researchers")

PEOPLE = {
    "demo_realist": {
        "hidden": {"realism": 1.0, "grounding": 0.8, "simplicity": 0.3, "novelty": -0.1,
                   "cost": -0.4, "risk": -0.7, "validity_care": 1.2},
        "research": [
            "Evaluations should look like real deployment. We built our benchmark from real users "
            "and real-world logs, because naturalistic data is the only evidence that transfers. "
            "Every result needs a sanity check and a control; a faithful measurement beats a clever one.",
            "I am skeptical of bold moonshot benchmarks. Start with a simple baseline and an ablation, "
            "measure carefully, and watch for confounds that threaten validity.",
        ],
        "other": [
            "Cooking notes: I never buy expensive gadgets; a cheap cast iron pan is efficient. "
            "I always taste and check the recipe twice, careful with salt. Grounded, concrete steps.",
        ],
    },
    "demo_contrarian": {
        "hidden": {"realism": 0.1, "grounding": -0.2, "simplicity": 0.6, "novelty": 1.2,
                   "cost": 0.2, "risk": 0.9, "validity_care": -0.3},
        "research": [
            "The interesting work is in unexplored, surprising directions. I like bold, ambitious, "
            "high-risk bets and novel creative setups; incremental realism tweaks are overrated.",
            "Keep the idea simple and minimal, then make a weird new direction work. Novel framings win.",
        ],
        "other": [
            "Travel blog: took a risky bet on a random overnight train, gamble paid off. New direction, "
            "never against a weird detour. Simple packing, minimal plans.",
        ],
    },
}


def main(n=160, seed=0):
    rng = random.Random(seed)
    for slug, spec in PEOPLE.items():
        root = os.path.join(ROOT, slug)
        os.makedirs(os.path.join(root, "corpus"), exist_ok=True)
        for kind in ("research", "other"):
            for i, txt in enumerate(spec[kind]):
                open(os.path.join(root, "corpus", f"{kind}__doc{i}.txt"), "w").write(txt + "\n")
        w = spec["hidden"]
        with open(os.path.join(root, "choices.jsonl"), "w") as f:
            for _ in range(n):
                a = {k: round(rng.random() * (rng.random() < 0.5), 2) for k in FEATURES}
                b = {k: round(rng.random() * (rng.random() < 0.5), 2) for k in FEATURES}
                u = sum(w[k] * (a[k] - b[k]) for k in FEATURES) + rng.gauss(0, 0.3)
                f.write(json.dumps({"a": a, "b": b, "chosen": "a" if u > 0 else "b",
                                    "context": "pick the next experiment"}) + "\n")
        json.dump(w, open(os.path.join(root, "hidden_weights.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
