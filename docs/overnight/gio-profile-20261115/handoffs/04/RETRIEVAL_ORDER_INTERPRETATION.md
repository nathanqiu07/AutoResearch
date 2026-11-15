# Retrieval order comparisons measure the full pipeline

The frozen retrieval diagnostic changes the interpretation of existing option-reversal comparisons. For semantic retrieval, changing option order can change the retrieved context as well as the options shown to the consumer. Those comparisons therefore measure option-order sensitivity of the whole pipeline; they do not isolate consumer position sensitivity.

Role 05’s saved-profile diagnostic covers 336 profiles and 168 reversal comparisons, all repeated views of the same 14 underlying judgments. Lexical retrieval preserves the rendered context in all 84 comparisons. Semantic context changes in 5 of 42 sparse comparisons and 9 of 42 richer comparisons. Five changes only reorder the same passage multiset; nine change exact-span membership or truncation boundaries.

At the selected 8,192-byte cap, semantic context changes in 4 of 14 sparse pairs (two order-only, two span/boundary changes) and 6 of 14 richer pairs (three of each). Exact-span differences do not measure semantic difference. These counts do not establish an effect on prediction flips or accuracy, and they do not establish a general advantage of either corpus.

This interpretation addendum changes no profiles, queries, embeddings, target items, scores, scaling selection or runtime. It does not define a new study. No private labels or prediction bodies were read for it. The repeated caps, methods, orders and source conditions add no independent judgments or source groups.

Source: role 05 handoff `024-retrieval-order-sensitivity-ready.json` (SHA256 `d128fd908c572f5d85775033c5de8809b730e752ebcdee45e2985294dc55ea1e`) and compact summary `024-retrieval-order-sensitivity-summary.json` (SHA256 `268d72b178c90c80707af10081e15629ca32ac308e26098e9ea2c9bed492af5a`). The evaluator checked these pins and summary arithmetic; role 05/root performed the saved-profile rendering audit. This handoff does not claim a second independent rendering audit.
