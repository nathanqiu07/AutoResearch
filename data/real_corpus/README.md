# Real user messages (discriminator reference)

`wildchat_sample.jsonl`: 200 English first user turns from `allenai/WildChat-1M`
(Hugging Face datasets-server rows API, first rows of the train split), fetched with
`python3 -m autoresearch corpus --n 200`. WildChat is released by AI2 under ODC-BY;
see the dataset card for terms. Messages outside 40–3000 characters are skipped at load time.

Known confound: these real messages cover arbitrary topics, while generated environments
are workplace tasks. The discriminator is told to ignore topic and judge style only, but
some topic leakage likely remains, so read the `discriminated` column as an upper bound on
detectability.

## Record format

Each `*.jsonl` file has one JSON object per line. Required: `"text"` (the first user
message). Optional: `"topics"` (list of tag strings) and `"source"` (string). When
absent, `load_corpus_records` fills `topics` from the keyword tagger and `source` from the
file stem. A present `topics`/`source` always wins, so a file tagged later by an LLM can
override the heuristic. `topics` must be a non-empty list of strings or loading fails.

## Topic taxonomy

Tags (see `TOPIC_RULES` in `autoresearch/research/corpus.py`): coding, data_analysis,
writing_editing, business_ops, customer_support, research_science, education,
legal_finance, health, personal_advice, creative, travel_lifestyle, other.
`topic_tags(text)` is multi-label and returns `["other"]` when no rule hits. It is a
keyword heuristic: expect misses and some wrong labels.

## Matching and fallback

`matched_pool(records, item_text_or_topics, min_matched=15)` returns the real messages
sharing at least one tag with a benchmark item, plus an info dict
`{"topics", "n_matched", "fallback", "n_total", "length_matched"}`. If fewer than
`min_matched` messages match, it returns the whole pool with `fallback=True`; report that
run as NOT topic-matched. Optional `length_band` (with `user_text`) also keeps messages
within a factor of the item's user-turn length, only if enough survive.

## Fetching more data (needs the user's approval)

This downloads from Hugging Face, so it runs only when the user says so. The existing
`corpus` command takes the first N English rows:

    python3 -m autoresearch corpus --n 200 --name wildchat_sample

Topic-balanced fetching is `fetch_hf_rows_by_topic` in `corpus.py`. It has no CLI flag yet;
run it from Python after approval (it reads at most `max_rows` rows, default 5000):

    python3 -c "from autoresearch.research.corpus import *; print(fetch_hf_rows_by_topic('allenai/WildChat-1M', 'default', 'train', ['coding', 'data_analysis', 'business_ops', 'customer_support', 'legal_finance', 'health'], 40, wildchat_first_user, name='wildchat_by_topic'))"

It prints the file path and per-topic counts; a count below the target means the row cap
was hit first. Web search (Exa) is not used for real messages: search results are forum
posts and articles, not user-to-assistant first turns, so they would add a new style confound.
