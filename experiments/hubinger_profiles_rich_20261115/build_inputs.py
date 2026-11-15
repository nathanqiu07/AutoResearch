#!/usr/bin/env python3
"""Build two method-specific prompts from one frozen neutral evidence packet."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "runs/nine-profile-petri/lanes/evan_hubinger-P8/evidence-ledger.jsonl"
OUT = ROOT / "runs/rich-profile-demo/hubinger"
MAX_ITEMS_PER_SOURCE = 2

ATTRIBUTION_ORDER = {"researcher_explicit": 0, "collaborative_work": 1, "inference": 2}
KIND_ORDER = {
    "change": 0,
    "research_decision": 1,
    "preference": 2,
    "conditional_rule": 3,
    "tension": 4,
    "method": 5,
    "belief": 6,
}

COMMON_RULES = """Use only the evidence packet below. It was selected deterministically from a frozen, quote-verified ledger; quote verification establishes textual provenance, not speaker attribution or truth. Preserve source identifiers exactly in square brackets throughout. Prefer 1–3 pertinent identifiers per paragraph or tight group of paragraphs. Do not add a bibliography.

Distinguish direct researcher statements, collaborative findings, and inference. A coauthored paper does not automatically establish a personal preference. Do not infer private biography, current beliefs, or a chronological change unless the evidence explicitly supports it. Treat repeated versions and discussions of one project as related evidence, not independent replication. Include concrete examples and material counterexamples. Output only a polished Markdown profile of 3,000–4,000 meaningful prose words with useful section headings. Do not mention this prompt, the evidence-selection script, downstream Petri results, or profile-fidelity scores.
"""

METHODS = {
    "synthesizeme": """Write a SynthesizeMe-inspired, corpus-based researcher persona for Evan Hubinger. This is an adaptation of persona synthesis to public research writing, not a reproduction of preference-data fitting.

Organize the profile as a coherent but corrigible model of how he tends to choose research problems and methods. Develop a small number of high-value hypotheses about recurring priorities, decision habits, tradeoffs, and standards. For each, show representative decision demonstrations: the situation, alternatives or tension, observed choice, stated or inferred reason, and what the example does not establish. Include boundary conditions and disconfirming examples. Make the result useful for anticipating how he might assess a new research plan without pretending to predict a held-out answer. Avoid a generic biography and avoid flattening the persona into universally admirable research virtues.
""",
    "icai": """Write an ICAI-inspired, corpus-based research constitution for Evan Hubinger. This is an adaptation of inverse constitutional principle extraction to public research writing, not a reproduction of preference-data fitting.

Organize the profile around a compact set of conditional principles that explain recurring research choices. Each major principle should state what is preferred over what, under which conditions, and why; then develop supporting cases, exceptions, conflicts with other principles, and evidence that would narrow or overturn it. Explain how principles combine when they point in different directions. Include concrete decisions and negative results. Avoid an unranked list of generic virtues: the constitution should expose distinctive tradeoffs, scope conditions, and unresolved composition rules.
""",
}


def main():
    rows = [json.loads(line) for line in SOURCE.read_text().splitlines() if line.strip()]
    by_source = {}
    for index, row in enumerate(rows):
        by_source.setdefault(row["doc_id"], []).append((index, row))

    selected = []
    for doc_id in sorted(by_source):
        candidates = sorted(
            by_source[doc_id],
            key=lambda pair: (
                ATTRIBUTION_ORDER.get(pair[1].get("attribution"), 9),
                KIND_ORDER.get(pair[1].get("kind"), 9),
                pair[0],
            ),
        )
        selected.extend(row for _, row in candidates[:MAX_ITEMS_PER_SOURCE])

    OUT.mkdir(parents=True, exist_ok=True)
    packet = OUT / "common-evidence.jsonl"
    packet_lines = []
    for row in selected:
        compact = {key: row.get(key) for key in (
            "doc_id", "claim", "attribution", "kind", "context", "uncertainty"
        )}
        packet_lines.append(json.dumps(compact, ensure_ascii=False))
    packet.write_text("\n".join(packet_lines) + "\n")
    evidence = packet.read_text()

    for method, method_rules in METHODS.items():
        directory = OUT / method
        directory.mkdir(parents=True, exist_ok=True)
        prompt = method_rules + "\n" + COMMON_RULES + "\nEVIDENCE PACKET START\n" + evidence + "EVIDENCE PACKET END\n"
        (directory / "prompt.txt").write_text(prompt)

    summary = {
        "source_ledger": str(SOURCE),
        "source_rows": len(rows),
        "source_documents": len(by_source),
        "selected_rows": len(selected),
        "selected_documents": len({row["doc_id"] for row in selected}),
        "max_items_per_source": MAX_ITEMS_PER_SOURCE,
        "method_prompts": sorted(METHODS),
    }
    (OUT / "input-summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
