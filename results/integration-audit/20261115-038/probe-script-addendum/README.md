This additive section retains the exact two neutral-probe script files explicitly released after audit 038's original source map. The original map's unresolved classification and all audit 035 artifacts remain unchanged.

`retained/probe-scripts.tar.gz` contains two Python files totaling 21,846 source bytes. SHA256 is `762133227fb664f14aac88957453104552d11f80b569f5b2cb2c5df195e90058`. The receipt SHA256 is `3cb2042dc05e8609247b7a7ab8da33eb383d5b3bfd42dc5abe7130d6132a867f`. Both original files matched the released hashes before and after capture. Static screening found no recognized credential patterns or nonempty sensitive literal bindings. No imports, execution, environment reads or provider calls occurred.

The script hashes match the corresponding recorded script hashes in audit 035's frozen `dispatch-binding/final/report.json`, SHA256 `f73ad4eb18d04a20e055debab94cc64a9ad753e720865230fccf56eff38fa1e0`. That report supplies the separately identified raw dispatch, canonical dispatch and raw summary hashes. This addendum uses those previously verified records; it does not reopen the private dispatches or summaries.

The archive-only byte verifier passes 32 checks. A separate AST-only checker passes 16 checks: the access script's module-level literal `PROMPT` is 65 UTF-8 bytes and hashes to `ef883a7e171b368fcc613467fd9fdad21eebc15a9df86355e3b2031d5aad2883`; the readiness literal is 69 bytes and hashes to `fd24dbf4371fd82a232c2eea716edd9384b3d9f5317b1aeebd3e7f39ce0ea03d`. These hashes match all three corresponding saved-call prompt hashes. The report contains no prompt prose.

The initial retention receipt and byte-verifier report precede the static literal check, so their statement that prompt reconstruction was not performed is a preserved scope statement for that earlier step. The later checker closes only the literal-to-record binding. It does not prove that the literal reached the provider, reconstruct complete system/caller/request behavior, authenticate network execution, or join unknown build requests. Immutable Git membership is not inferred from a released file path or runtime commit.

Run from this addendum directory with the prior public evidence tree available:

```sh
python3 -I -B verify_probe_retention.py \
  --archive retained/probe-scripts.tar.gz \
  --receipt retained/retention-receipt.json \
  --receipt-sha256 3cb2042dc05e8609247b7a7ab8da33eb383d5b3bfd42dc5abe7130d6132a867f \
  --binding-report /path/to/audit-checkout/results/integration-audit/20261115-035/dispatch-binding/final/report.json \
  --out /path/to/fresh-probe-byte-verification.json
```

For the literal binding, run the same arguments with `static_prompt_binding.py` and another fresh output path. Neither command imports or executes retained source or opens its original paths. The historical capture command is preserved in `retention-invocation.json`; capture refuses an existing output directory.
