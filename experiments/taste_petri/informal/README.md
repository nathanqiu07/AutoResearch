# informal: Owain Evans's informal pre-T material and the decisions in it

Input for `synthme/PROTOCOL.md` (the S_inf arm). T = 2026-01-01; every source is public and dated before T.
Built by `build.py` (`collect` -> `extract` -> `speaker` -> `assemble`); nothing outside this directory was written.

## Files
- `raw/`: what was fetched. axrp.net and theinsideview.ai pages over plain HTTP; YouTube auto-captions for two
  interviews via Exa (the agent-reach subtitle route returned HTTP 429); four threadreaderapp pages over HTTP;
  all of his LessWrong/AF comments from the public GraphQL API (`userId spJZRySQgiKAFTtHp`, with each parent comment).
- `texts/`: one text per source (`texts/comments/lw_<id>.md` per comment, holding the parent comment as context
  and his comment). Labeled transcripts also have `<id>.owain.txt` (his turns only), and podcasts have the
  `<id>.partN.txt` chunks that were sent for extraction.
- `sources.jsonl`: 207 sources (source_id, register, url, date, title, text_path, in_paper_set, chars).
- `groups.json`: the 30 extraction calls (podcast chunks of about 32k chars; comments batched by about 15k chars of his text).
- `decisions.jsonl`: **259 verified items from 103 distinct sources**.
- `dropped.jsonl`: the sources that were left out, with reasons. `stats.json`: drop counts per register.
- `calls.log`, `cache/`: **39 sonnet calls and 4 haiku calls** (caps 120 and 100; 3 concurrent; about $3.07 in total).
  21 of the sonnet calls built the final file. The other 18 came from a first pass with unchunked podcasts and 30k comment
  batches; their cached outputs are unused.

## Item schema
The decision_v2 fields (`point` D1-D6, `problem`, `did`, `alternatives_named` as a list, `stated_reason`, `quote`)
plus `item_type` (decision / rejected / disagreement / advice), `register`, `source_id`, `source_url`, `date`,
`title`, `speaker_verified`, `speaker_check`, `in_paper_set`, `researcher`, `split` = pre, `cutoff`, `work_id`
(`owain_evans:informal:<source_id>`) and `decision_id`.

Checks (an item is dropped if any fails): `did` is non-empty; no field matches Hobbhahn or SAD; the quote passes
`timesplit.quote_in_text` against the source; the quote is 15-60 words; there is no duplicate quote within a source;
and the speaker check passes. In a comment, the quote must come from his own text, not the parent comment and not a
`>` blockquote. In a labeled transcript (AXRP, Inside View), the quote must be inside his turns. The two
auto-caption transcripts (TDS, QURI) have no labels, so sonnet's `speaker` field and a haiku check that reads the
surrounding captions must both say "owain". On threads, posts, slides and comments he is the sole author.

## Counts per register
| register | sources (with items / total) | raw | kept | decision / rejected / disagreement / advice | dropped: quote not found / length |
|---|---|---|---|---|---|
| podcast | 4 / 4 | 77 | 75 | 27 / 1 / 8 / 39 | 2 / 0 |
| comment | 88 / 188 | 117 | 115 | 13 / 4 / 28 / 70 | 0 / 2 |
| thread | 5 / 5 | 47 | 43 | 33 / 0 / 1 / 9 | 0 / 4 |
| advice | 1 / 1 | 12 | 12 | 0 / 2 / 0 / 10 | 0 / 0 |
| shortform | 2 / 5 | 7 | 7 | 1 / 0 / 1 / 5 | 0 / 0 |
| ideas | 1 / 1 | 4 | 4 | 3 / 0 / 1 / 0 | 0 / 0 |
| ama | 2 / 3 | 3 | 3 | 0 / 0 / 2 / 1 | 0 / 0 |
| **total** | **103 / 207** | 267 | **259** | 77 / 7 / 41 / 134 | 2 / 6 |

No item failed the speaker check or the Hobbhahn/SAD field filter. The SAD material was removed before extraction (see below).

Podcasts: AXRP 42 (2025-06-06, Daniel Filan), The Inside View (2024-08-23, Michaël Trazzi), the Towards Data Science
podcast (2021-01-13, auto-captions), and a QURI discussion with Ozzie Gooen (2023-04-30, auto-captions). The threads
are the Emergent Misalignment thread (2025-02-25), InstructGPT probing (2022-02-23), Reversal Curse (2023-09-22),
Looking Inward (2024-10-18) and Weird Generalization (2025-12-11). Items span 2019-2025: 2025 has 75, 2021 has 55
and 2023 has 38.

## Caveats for SynthesizeMe
- **Overlap with the paper set:** 25 items come from three corpus docs that `profiles_contrastive/decisions_pre_t.jsonl`
  already uses: project ideas, empirical-research tips and the EM thread (`in_paper_set: true`). Drop them for a
  clean papers-vs-informal comparison. The four paper-announcement threads (InstructGPT is not one of them) cover
  the same works as papers in that set, but they were extracted separately here.
- **Off-topic comments:** about 43 comment items are on Covid/epidemiology and other non-AI posts (2020-2022).
  They are reasoning about evidence, not AI-research choices. Filter them on `title` if needed.
- Most items are `advice` (134), so few of them contain a binary choice with a named alternative.
- The auto-caption quotes keep the caption errors (lowercase, "um", misheard words), because they were verified
  verbatim against the captions.

## Dropped (see `dropped.jsonl`)
- **Hobbhahn rule:** 5 comments on the SAD post (Hobbhahn is a co-author) and 1 on "Should we publish mechanistic
  interpretability research?" (Hobbhahn is an author). From The Inside View, the first 45,937 chars (the highlights and
  the whole SAD section) were never sent for extraction; only the Out-of-Context Reasoning section and the Twitter
  questions were. The Hinton Lectures 2025 were also left out: they are general-audience lectures with no published
  transcript, YouTube was rate-limited, and lecture 3 presents Apollo/OpenAI work co-authored by Hobbhahn.
  "Lessons from studying two-hop latent reasoning" is an arXiv paper that is already in the paper set and mentions Hobbhahn.
- **Post-T:** 80,000 Hours #252 (2026-08-20; the manifest's podme URL is the same episode), Three half-baked research
  ideas (2026-11-08), the LinkedIn post "Some background reading" (2026-08-08), and four threads from 2026.
  The five LW comments dated after T were skipped.
- **Duplicates or unrelated:** the Cognitive Revolution crossover is a re-broadcast of The Inside View. The manifest's
  other YouTube URLs (live, shorts, clip, m.youtube) are not him.
- **Too short:** 15 comments have fewer than 15 words of his own text.
- **Not used:** the corpus shortform post holds only an index without bodies, so the 5 shortform comments came from
  GraphQL instead. The corpus AMA doc is the question post, and his 2 answers came from GraphQL.

## Five examples
1. **podcast, AXRP 42, 2025-06-06, decision D2.** Problem: whether to measure introspection in off-the-shelf models or after fine-tuning. Did: fine-tuned on self-prediction after finding the models were bad at it without fine-tuning; he treats this as eliciting an existing ability. Alternative: asking models directly without fine-tuning.
   Quote: "we did try that and we just found that models were really bad at this task. So models did not seem to have this introspective ability without any fine-tuning. But this is a pretty common thing. Models generally aren’t very good at things unless you train them on those things."
2. **podcast, QURI, 2023-04-30, decision D1.** Problem: how to define truthfulness when saying nothing avoids all falsehood. Did: defined it so that a silent model counts as perfectly truthful, so truthfulness is kept apart from informativeness. Alternative: treating truthfulness as calibration.
   Quote: "the way we Define truthfulness in these works is that a model could be perfectly truthful if it just never said anything and and generally yeah it's it's uh you know one way to avoid falsehood is just to avoid you know statements where you have a small amount of uncertainty"
3. **comment, on "How truthful is GPT-3?", 2021-09-16, disagreement D5.** Did: rejected a commenter's single-prompt conclusion that the "I have no comment" instruction drives uninformative answers; the paper's ablations show otherwise. Alternative: concluding from a handful of example prompts.
   Quote: "The prompt you tried (which we call “helpful”) is about as informative as prompts that don’t include “I have no comment” or any other instructions relating to informativeness. You can see the results in Appendix B.2 and B.5."
4. **advice, Tips on empirical research slides, 2025-01-08, advice D6.** Did: put the raw ingredients (prompts, error bars) in the slides, not only the conclusions, so that others can critique the experiment. Alternative: presenting only high-level conclusions.
   Quote: "Part of the reason for showing the prompt and error bars is that you want people in the meeting to critique the experiment. So you want to have the “raw ingredients” in the slides, not just the high-level conclusions you are drawing (which might be wrong)."
5. **thread, InstructGPT probing, 2022-02-23, decision D1.** Did: when probing for alignment failures, included prompts about scientific misconduct and bad-faith reasoning (p-hacking after a null result, spinning a failed quality test) as well as overtly criminal requests.
   Quote: "Will InstructGPT suggest that I do something like “p-hack” after a failed experiment? Yes! If the main effect of an intervention was not significant, it recommends fishing for a sub-group with a significant effect."
