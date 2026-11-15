# Saved P8 profiles can now be exported for the auditor

The offline exporter accepts the selected Neel Nanda and Chris Olah P8 profiles. It preserves their complete statements, source references, conditions, dates, relations and null weights. Their confidence remains uncalibrated. It makes no model calls and does not refit a profile.

**This is an export, not a new experiment or completed runtime integration.** The existing Petri preparer still accepts only its frozen Hobbhahn SynthesizeMe M2 artifact. The completed shutdown comparison remains M2. No P8 benefit has been measured in that comparison.

The full original profile stays byte-for-byte intact in `profile-original.json`. `auditor-context.txt` contains the full content plus identity and status fields, with a fixed preface explaining its limits. `provenance.json` retains every original metadata field and lists which fields are outside the model-facing context. No statement is ranked, paraphrased, deleted or turned into a permanent rule. Some statements are beliefs or descriptions, not preferences.

The exporter checks the selected file and identity, internal hashes, config consistency, original byte cap, and P8 structure. Its digest format matches the existing neutral-profile contract. It does **not** reread source documents, verify semantic entailment, confirm the researcher's preferences, or test usefulness. A checksum proves integrity relative to a supplied selection; it does not prove that a claim is true.

## Run it locally

From the repo root, run the synthetic fixture tests without credentials:

```bash
PYTHONPATH=scripts/gio_petri python3 -m unittest scripts/gio_petri/test_neutral_profile_adapter.py
```

The verified private exports already live under:

```text
~/.local/share/autoresearch/exports/gio-p8-auditor-context-v1/neel_nanda/
~/.local/share/autoresearch/exports/gio-p8-auditor-context-v1/chris_olah/
```

Open `auditor-context.txt` to read exactly what the future auditor context would contain. These are actual saved profile exports, not the synthetic test fixtures. The exports are kept local; their content is not included in this publication.

To reproduce Neel's export into a **new** directory on this machine:

```bash
python3 scripts/gio_petri/neutral_profile_adapter.py \
  --profile "$HOME/.local/share/autoresearch/exports/gio-p8-auditor-context-v1/neel_nanda/profile-original.json" \
  --expected-sha256 371f2ea185a9ca64d94f935ed863bc08ae50ae3250d35c062f6602be3cb2b177 \
  --expected-profile-id 62b1d0a94424408548733676359d2e4209e6a00f38c69b3e564e29b5fa64732d \
  --expected-researcher-id neel_nanda \
  --expected-replicate-id 0 \
  --out /tmp/neel-p8-auditor-example
```

For another approved artifact, obtain expected identity values from its independent selection record. Do not derive a new expected hash merely to bypass a rejected input. Existing output directories are never overwritten. Directories use mode0700 and files0600.

The Python entry points are `render_saved_p8_context(profile_path, **expected_identity)`, `export_saved_p8_context(profile_path, out, **expected_identity)`, `auditor_template_suffix(context, recipient='auditor')`, and `verify_export(out)` in `scripts/gio_petri/neutral_profile_adapter.py`.

## What remains before a P8 run

A future preparer must explicitly put the exported suffix in the auditor template, pin the exact source and exported bytes, and define a suitable comparison control. `auditor-suffix.template.txt` escapes literal braces for Petri's formatting step. It is not a seed, a target prompt, a judge prompt or an execution packet.

The helper rejects a target or judge recipient. That is an API boundary, not proof of isolation in a live pipeline. A future integration test must verify the final target/judge requests and ensure that profile text is not copied into environment files. A new approved run and budget lease would then be needed. No such run is queued here.

The original two profiles passed the authoritative envelope validator and this exporter, with network sockets disabled and no OpenAI or Inspect model modules imported. Full content equality, exact source copies, original-source immutability and template round trips passed. See [verification metadata](verification.json), [independent code review](independent-review.json), and [design](design.md).
