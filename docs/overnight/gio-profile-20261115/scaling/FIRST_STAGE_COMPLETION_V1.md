# First scaling stage: completion metadata

Sol and Astra completed the first fixed-profile B plus mandatory-control stage. Closed admission,
batch-verification and dispatch-receipt metadata reconcile to **124 new jobs and 280 completed
request slots**. These are 280 actual draws with 278 distinct BODY identities. Two same-input
lexical/semantic pairs—one Neel item on Sol and one on Astra—remain separate completed draws and
paired evidence. They are not automatically collapsed or treated as independent judgments.

The stage also references 62 original Luna jobs containing 140 ordered-row aliases. These add zero
new calls and zero incremental stage cost. There are 420 logical ordered rows in total. Reversed
option orders remain paired judgments. D uses the same 84 raw-control row references and adds no
calls. This index contains no fidelity score, correctness label or capability finding.

## Exact completion index

`/private/tmp/gio-profile-20261115-scaling/first-stage-completion-metadata-v1-iat6jrgt/completion-index.json`

SHA256: `d6906181c9043f0a75f0194277eb5a1566931aaf55eada91868236e4a3a19880`.

A byte-identical durable copy is published beside this document as
`first-stage-completion-index-v1-d6906181c9043f0a75f0194277eb5a1566931aaf55eada91868236e4a3a19880.json`.
Both copies contain metadata only.

The safe index contains actual admitted job IDs, original unleased draft references, prepared
packet/manifest hashes, completed receipt references, request identities under the owner's BODY
and endpoint-plus-BODY conventions, profile/source/item hashes, ordered-item schedules, original
Luna lineage, duplicate wire groups and cost ownership. Result/profile/source bodies were not
opened; their exact references remain opaque. Costs belong to actual jobs and are counted once,
without inventing per-item spend splits.

| Model | New jobs | New draws | Incremental known usage estimate |
| --- | ---: | ---: | ---: |
| Sol | 62 | 140 | $0.512080 |
| Astra | 62 | 140 | $2.387300 |
| Total | 124 | 280 | $2.899380 |

Astra's terminal 280 attempts/$2.899380 is **cumulative on the same ledger**. Its prior baseline is
Sol's 140 attempts/$0.512080; Astra's increment is 140 attempts/$2.387300. The generator verifies that
difference against the explicit Astra tranche fields and the sum of its actual job receipts. These
are known conservative usage estimates, not invoice costs. Closed receipts report zero new cache
hits and zero uncertain attempts. No live SQLite or native claim files were inspected.

The 120 baseline jobs / 224 draws account for $2.355260 (Sol $0.415910, Astra $1.939350), with 222 distinct
BODY inputs. The four saved-primary P8 B jobs / 56 draws account for $0.544120 (Sol $0.096170,
Astra $0.447950). Role05 owns the independent baseline audit; Role04 owns scoring. This artifact
combines metadata and checks bookkeeping without repeating those audits.

The no-profile artifact retains canonical cap 2048 and its original profile hash. It is an
empty-render alias into logical cap 8192, not a retagged profile. Other profiles retain cap 8192.
The source-condition, semantic-retrieval reversal and source-group limits from earlier handoffs
still apply. Existing owner01 dual-convention admission/wrapper evidence remains separate; the
indexer does not create a new guard, driver or execution authorization.

## Pins and bounded reproduction

| Input | SHA256 |
| --- | --- |
| Sol actual admissions | `ba96f2c68641e9d2f6bc281e8657f068ee88691261c016c5069b34b9240946e2` |
| Sol closed terminal | `563d56a7ec180a8c0562eef06eaf1f81f68ae5f1469289a4d77dbfa82baa7e78` |
| Astra actual admissions | `7a38c2686d87e1631566e381af43246d35eb83e71d8890508675d8fbb3f4c011` |
| Astra closed terminal | `a58489d8b922eaeb8f05a03346d231f0f8228f864c8aacf42a6328068670bcc4` |
| Original first-stage bindings | `2f29c267b7eab6da7e28e53868a5427da3ec0d36494fda3864d81e39d61e0822` |
| Role05 wire-binding check | `8cd9edfe03f2f6ad1ce74f7c6ac15d361e01348fcafbaf1f9ae8269d2e10f107` |

The metadata-only generator is `index-first-stage-completion-v1.py`, SHA256
`362a81eec649094b323dcac54081378227123a89b195c810f575728376e74344`.
It does not import or run any producer, preparation recipe, dispatcher, provider or scoring code.
It verifies all read metadata hashes again at the end and writes a new private index directory.
The underlying runtime remains `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`.

```sh
python3 docs/overnight/gio-profile-20261115/scaling/index-first-stage-completion-v1.py
```

No model calls, gold labels, score files, result/profile/source bodies, native claims or live
SQLite were accessed by this task. Reuse the pinned index unless another metadata reconstruction
is necessary. Four new P8 build outputs and their 56 joint plus 28 crossed predictions are separate
future dependencies; no identity or outcome for those instances is inferred here.
