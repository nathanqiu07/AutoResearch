# Rich researcher profiles: Carlini and Steinhardt

Five source-grounded profiles per researcher, prepared from existing repository
corpora and extraction artifacts. Each profile contains more than 3,000 words.
These are candidate models of research judgment, not validated predictions of
the researcher's preferences or endorsements by the researcher.

| Method | Technical name | What the profile represents |
|---|---|---|
| P2 | Research-Process Reconstruction | A narrative of research questions, methodological decisions, and how evidence changes the argument. |
| P5 | Conditional Decision-Rule Induction | Context-dependent decision rules, their rationale, exceptions, and concrete examples. |
| P8 | Contrastive Interpretive Modeling | Competing interpretations of research taste, with supporting evidence, tensions, and ways to distinguish them. |
| SynthesizeMe-inspired | Persona Synthesis | An integrated working persona grounded in documented research decisions. |
| ICAI-inspired | Constitutional Principle Induction | A set of conditional principles with priorities, conflicts, and revision conditions. |

The last two are adaptations to researchers' writings. They do not reproduce
preference-data fitting, example selection, or optimization from the original
methods. The five documents share evidence and are not independent observations.
The method names match the earlier Hubinger package; this package does not claim
an identical extraction or generation pipeline.

## Profiles

| Researcher | P2 | P5 | P8 | SynthesizeMe-inspired | ICAI-inspired |
|---|---|---|---|---|---|
| Nicholas Carlini | [P2](nicholas_carlini/P2.md) | [P5](nicholas_carlini/P5.md) | [P8](nicholas_carlini/P8.md) | [Persona](nicholas_carlini/SynthesizeMe.md) | [Principles](nicholas_carlini/ICAI.md) |
| Jacob Steinhardt | [P2](jacob_steinhardt/P2.md) | [P5](jacob_steinhardt/P5.md) | [P8](jacob_steinhardt/P8.md) | [Persona](jacob_steinhardt/SynthesizeMe.md) | [Principles](jacob_steinhardt/ICAI.md) |

The [Hubinger package](../hubinger_petri_20261115/) contains the corresponding
five profiles for Evan Hubinger.

Each researcher directory includes `SOURCES.json` with pinned GitHub source links for resolving citations and
`BUILD_NOTES.md` for evidence selection and attribution limits. The root
`profiles.json` records exact word counts and SHA-256 hashes of the finished
profiles. Word counts use whitespace-separated tokens; they are not model-token
counts or measures of evidence coverage.

## Use in comparisons

Keep the profile text, task, context recipient, model settings, and controls
explicit. A difference between generated profiles is not itself evidence that
they produce different decisions or improve evaluation quality. No new Petri
experiment is included in this package. Hypothetical examples in a profile are
illustrations of the inferred rule, not additional biographical evidence.

Source identifiers refer to existing public-writing corpora. Coauthored papers
support claims about the collaboration; they do not establish which author made
each decision. Direct statements, observed choices, and inferred preferences
must remain distinct when these profiles are reused.

See `validation.json` for the file checks and limits of the source spot checks.
