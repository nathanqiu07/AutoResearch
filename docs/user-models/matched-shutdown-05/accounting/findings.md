# Cost correction and archive closeout

The saved ledgers omitted cached input tokens from some paid judge calls. Their totals therefore do not support the earlier label “conservative uncached estimate.” This correction changes the cost interpretation, not any experiment result. Original ledgers, requests, replies and failed reviews remain unchanged.

For example, one saved batch05 judge response reports 20,412 input tokens, including 9,088 cached tokens. The normalized usage object records 11,324 noncached input tokens and 9,088 cached tokens separately. The old cost helper priced only the 11,324. It did not add a separate cached-input charge. Seven paid batch05 calls have this issue, covering 40,832 cached tokens.

The table below applies the **same saved input and output rates to every raw input and output token**, without a cache discount. It is a reference estimate—not a provider invoice, account balance, current-price claim, or evidence of a budget overrun.

| Run | Recorded OpenAI estimate | All raw input at the same saved rates | Difference |
|---|---:|---:|---:|
| Baseline 01 | $0.14076000 | $0.14556000 | $0.00480000 |
| Baseline 02, including postmortem | $0.09428250 | $0.09428250 | $0 |
| Matched 03 | $0 | $0 | $0 |
| Matched 04 | $0.74355250 | $0.80547250 | $0.06192000 |
| Matched 05 | $0.98371500 | $1.03475500 | $0.05104000 |
| Separate three-call review of 05 | $0.35727250 | $0.35727250 | $0 |

The OpenRouter arithmetic is unchanged. **Batch05 plus its separate review comes to $1.39202750 OpenAI + $0.03678950 OpenRouter = $1.428817**, using this full-input interpretation. The original ledgers still record $1.377777. The separate three-call review has no cached-input discrepancy in the saved responses.

[Open the comparison with the cost correction shown first](corrected-viewer/index.html). Its cost cards deliberately retain the original ledger values; the opening notice states the correction. [The separate judge review](../additive-review/index.html) remains unchanged.

## Spending allowances are not bills

There are four distinct modern execution leases: matched03, matched04, matched05 and the separate review. The earlier reservation-only record for05 refers to the same05 allowance; it is not a fifth allocation. Phase ledgers and published copies are views of the same calls, not extra charges. The audit checked 259 distinct saved response identities across the identified older and newer runs; this does not prove authenticated network traffic or cover all historical project spending.

The coordinator still reserves **$58 OpenAI and $31.000001 OpenRouter** for this closed track. This includes an older **$20 allowance per provider**, which remains intact because earlier project costs are not fully reconciled here. Do not add the verified older costs to that inclusive reserve again.

The $0.02584576 uncertain OpenRouter reservation from matched03 is retained. Baseline02 also has a stale pending ledger entry, but it belongs to a failed free-target response whose saved provider usage explicitly reports zero cost. Its original status is preserved; it is not evidence of an additional positive charge.

For the four modern leases, full-input saved-rate arithmetic is $2.19750000 OpenAI and $0.11190140 OpenRouter. Adding the03 uncertain allowance and preserving the full historical reserves would retain $22.19750000 OpenAI and $20.13774716 OpenRouter. The difference from gross allocations is $35.80250000 and $10.86225384. These are **conditional accounting figures for the coordinator**, not released funds or an account balance. This owner has released or reassigned nothing.

## The full earlier evidence is now durable

All six identified run bundles have exact private archives, including native `.eval` files where present. The three older bundles previously retained only in temporary storage were copied without changing their source files:

| Older bundle newly archived | Files | Bytes |
|---|---:|---:|
| Baseline01 | 51 | 1,596,503 |
| Baseline02 | 77 | 2,739,131 |
| Matched03 | 60 | 961,584 |

Archive copies match source hashes. Directories use mode0700, files0600; files, manifests, receipts and directories were synced to disk. Historical failure statuses and pending reservations are preserved. There were no new model calls, environment runs or held-out evaluations.

- [Cost interpretation, archive paths and receipt hashes](cost-interpretation.json)
- [Independent original05 cache evidence](independent-original05-cache-evidence.json)
- [Owner reconciliation draft and all raw-token rows](owner-reconciliation-draft.json)

The owner draft predates the independent confirmation of the omission and still labels that source question unresolved. Its arithmetic is retained as historical evidence; the confirmed interpretation above is separate. No old ledger or model output was corrected in place.
