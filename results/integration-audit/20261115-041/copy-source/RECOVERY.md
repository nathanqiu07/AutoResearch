This narrow capsule retains the exact public audit 039 package and handoff at Git commit b35c0f8f47f40b28a0aa6338fb7f626ce0db2b0f: 140 package files plus one handoff. The public archive is a Git tree snapshot of those exact paths. It is not a Git repository or a reconstruction of history.

The capsule also retains only the new 13-record private gap archive, SHA256 b05776948990821e627b4c902f505ad9a36fd86132b67999de2881c431faa492, 43,236 bytes. The public package already includes the 90-file runtime-source gap archive. The existing owner payload supplies 210 retained files serving 234 logical references. That payload is a required external dependency and is neither copied nor bundled here. Its recorded location is /Users/giordanorogers/.local/share/autoresearch/archives/gio-matched-shutdown-05/payload. A relocated payload can be supplied explicitly.

Obtain the capsule manifest SHA256 from the published audit 041 handoff or its pinned copy-manifest.json. Do not treat an unverified local manifest as its own authority. The copied manifest.json and copy-receipt.json record the manifest identity and copy result. All capsule files must be 0600 and directories 0700. Use standard Python without optimization flags that disable assertions in the exact reused copier/extractor.

Set explicit locations, choosing fresh report and recovery output paths:

```sh
CAPSULE=/path/to/downstream039-b35c0f8
CAPSULE_MANIFEST_SHA256=the_published_041_copy_manifest_sha256
PUBLIC=/fresh/private/public039
OWNER_PAYLOAD=/path/to/existing/gio-matched-shutdown-05/payload
REPLAY=/fresh/private/recovered039
```

First verify the copied capsule, including exact public member names and byte hashes against its retained Git-blob inventory. This command does not require original Git objects and does not open or extract the private archive contents:

```sh
python3 -I -B "$CAPSULE/tools/verify_capsule.py" \
  --root "$CAPSULE" --manifest "$CAPSULE/manifest.json" \
  --manifest-sha256 "$CAPSULE_MANIFEST_SHA256" --copied \
  --out /fresh/private/capsule-verification.json
```

Then use the exact audit 040 extractor. It requires a fresh destination, rejects traversal, links and special members, and creates private directories and files:

```sh
python3 -I -B "$CAPSULE/tools/recover_public.py" \
  --checkpoint "$CAPSULE" --manifest-sha256 "$CAPSULE_MANIFEST_SHA256" \
  --out "$PUBLIC"
```

The recovered public tree supplies the original and recovered audit readers. Replay uses the existing owner payload, the public90-file source archive and this capsule's private13-record archive. It does not need a checkout, original temporary paths, installed provider dependencies or Git fallback. The reader reads saved records and emits metadata; it does not make model calls.

```sh
ORIGINAL="$PUBLIC/results/integration-audit/20261115-039"
RECOVERY="$ORIGINAL/recovery"
python3 -I -B "$RECOVERY/reproduce_recovered.py" \
  --input-map "$RECOVERY/preparation-01/recovered-input-map.json" \
  --input-map-sha256 1c4cad7f68896c5dd9afc2b88bdf9f509d005a2343df395a1647a88964996dd3 \
  --inventory "$ORIGINAL/run-03/input-inventory.json" \
  --retained-root "$OWNER_PAYLOAD" \
  --source-archive "$RECOVERY/runtime-source-gap.tar" \
  --publication-archive "$CAPSULE/private/downstream05-audit039-publication-gap-v1.tar.gz" \
  --out "$REPLAY"

python3 -I -B "$RECOVERY/compare_recovery.py" \
  --original-report "$ORIGINAL/run-03/report.json" \
  --recovered-report "$REPLAY/report.json" \
  --original-inventory "$ORIGINAL/run-03/input-inventory.json" \
  --recovered-inventory "$REPLAY/input-inventory.json" \
  --changes "$RECOVERY/reader-change-proof.json" \
  --portable-reader "$RECOVERY/reproduce_recovered.py" \
  --out /fresh/private/replay-comparison.json
```

The previous pinned replay passed 1,316 checks with identical input inventory and report evidence; only argv and reader_sha256 differ. A new-location replay must be performed before claiming that location verified. Exact source/input recovery does not authenticate physical provider requests, invoices or old process execution, restore the unarchived Inspect normalizer, or include later judging repairs. This is a same-machine retention capsule, not off-device backup. The older 16 private archives and full owner archive are outside this copy scope.
