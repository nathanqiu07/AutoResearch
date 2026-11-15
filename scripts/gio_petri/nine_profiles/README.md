# Long profiles through native Petri

This prospective runner gives exact supplied text to the Petri auditor, then
records its authored shutdown environment, target interaction, initial-world
review, primary validity/awareness review, and legacy secondary measurements.
It never scores the profile. Earlier runners and results remain unchanged.

```sh
python scripts/gio_petri/nine_profiles/runner.py \
  --profile /path/to/profile.md --lane nicholas_carlini-P2 \
  --out /path/to/new-output --config /path/to/PETRI_CONFIG.json \
  --replicates 3 --credentials-file /path/to/authorized.env --execute
```

Omit `--profile` for the no-profile control. Generic and raw-source controls use
the same interface as profiles. Omit `--execute` to freeze and verify inputs
without calling a provider. An already prepared output can be executed once:

```sh
python scripts/gio_petri/nine_profiles/runner.py \
  --out /path/to/prepared-output --prepared \
  --credentials-file /path/to/authorized.env --execute
```

Use the existing Petri Python environment. The adapter needs `OPENAI_API_KEY`;
it parses an optional authorized dotenv file as data, never shell code. It uses
OpenAI Responses through native Inspect. Models and rates are explicit in the
configuration. Defaults are GPT-5.1 with medium reasoning for auditor/target,
high reasoning for judge, and 16,384 maximum output tokens. GPT-5.1 support and
400,000-token context were checked against the official model documentation;
the authorized provider's model list also confirmed availability.

Each replicate permits at most 30 auditor turns, 100 total provider calls, and
$8 in charges/reservations. A batch expires after three hours. Input tokens are
conservatively priced at the uncached rate; these are estimates, not invoices.
Every request reserves the full model context plus output allowance before
dispatch. Errors or unknown usage retain the reservation and stop the batch.
No automatic transport retries, output-directory reuse, or outcome-based
regeneration is allowed. Native Petri retains its bounded judge-format retries.

Input hashes cover the full profile, packet, configuration, and runtime Python
sources. The native target receives the auditor's environment, never the profile
as an explicit input. Primary review uses source-line references and the existing
substantive validity rubric; the adapter reconstructs exact citations. Initial
world reviews remain separate from behavioral outcomes.

Each completed attempt also checks actual provider captures: supplied context
must appear in an auditor request and must not appear wholesale in target or
judge requests. Missing captures remain incomplete, and failed checks cannot
count as valid comparison cases. This does not detect every partial paraphrase.
The empty control checks request coverage without treating an empty string as
context leakage. A common authoring instruction makes clear that workspace notes
are shown verbatim to the target and must contain only in-world task context.
An additive marker report flags experiment-author narration; it never rerolls or
removes a generated environment.

Interpretation limits: the clock and tools are simulated; no shutdown or target
application executes. Startup deliberately exposes shutdown. All model roles
share a model family. The legacy secondary measurements may clip long traces,
and post-hoc recognition is not a measurement of original private belief. Full
raw traces and individual failures remain available. Fixed-batch comparisons
must use the same settings and keep all declared failed/missing rows visible.
Provider-returned reasoning summaries are not raw or private chain of thought.
When reasoning is absent, the inherited secondary scorer remains unmeasured;
native Petri and primary-review awareness are still reported separately. No
missing secondary score is replaced with zero.

Tests:

```sh
python -m unittest discover -s scripts/gio_petri/nine_profiles -p 'test_*.py'
python -m unittest discover -s scripts/gio_petri -p 'test_*.py'
```

Sources: [model support](https://developers.openai.com/api/docs/models/gpt-5.1),
[standard prices](https://developers.openai.com/api/docs/pricing).
