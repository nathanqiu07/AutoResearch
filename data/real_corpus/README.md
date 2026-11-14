# Real user messages (discriminator reference)

`wildchat_sample.jsonl`: 200 English first user turns from `allenai/WildChat-1M`
(Hugging Face datasets-server rows API, first rows of the train split), fetched with
`python3 -m autoresearch corpus --n 200`. WildChat is released by AI2 under ODC-BY;
see the dataset card for terms. Messages outside 40–3000 characters are skipped at load time.

Known confound: these real messages cover arbitrary topics, while generated environments
are workplace tasks. The discriminator is told to ignore topic and judge style only, but
some topic leakage likely remains, so read the `discriminated` column as an upper bound on
detectability.
