# Overnight work: five coordinated lanes

Aim for a credible demonstration and a reusable research tool, with evidence of what works and what fails. More agents do not by themselves mean more progress. Use these five lanes: this main experiment chat, the existing integration-audit chat, and up to three new chats below. Send each new chat its complete prompt file. Do not start a second copy of an existing lane.

| Lane | Owner / prompt | Deliverable |
|---|---|---|
| Baseline and experimental execution | Current main chat; already active | Approved 30-turn baseline, validity review, full outputs even on failure. Only this lane currently has paid-run authority. |
| Integration audit | Existing chat `01a1de44-b76b-7290-9753-ba528b42819e`; [continuation prompt](integration.md) | Reproducible checks that saved profiles cause the intended model input, with implementation and artifact versions pinned. |
| Measurement and skeptical review | New chat; [prompt](measurement.md) | A small independent challenge set and primary-source review of what our metrics do and do not establish. |
| Researcher context | Coordinate with existing profile-search owner; [prompt](context.md) | One source-grounded Neel Nanda research context packet, direct excerpts baseline, and a small evaluation plan. No invented preferences presented as ground truth. |
| Demo and evidence browser | New chat; [prompt](demo.md) | A local browser demo driven by saved artifacts, with honest failure states and a short presentation narrative. |

The existing coordinator `01a1de5d-d544-7f10-b758-bcfbf7f22200` owns broad profile-search workers and Neel/Chris corpus intake. Do not duplicate those workers. The researcher-context prompt here is a separate, bounded consumer of the shared corpus; skip it if the coordinator already owns that output too.

## Shared operating rules

- Each chat uses its own `/goal`, branch, and checkout. No recurring task that repeatedly restarts experiments.
- One API spending authority: this main experiment chat. The $100 total is shared, not $100 per chat. Other lanes use existing artifacts, ordinary source browsing and deterministic offline checks; no paid API/GPU/batch jobs unless Gio explicitly gives an additional allocation from the shared budget.
- Do not change model IDs, providers, seed, generation settings, runtime judging, or shared teammate modules. Propose changes as a concrete patch or plan for the owner to review. Preserve held-out data. Do not open it for exploratory work.
- Keep existing results immutable. Preserve invalid cases and errors. Do not optimize until a lucky run looks good. Do not treat demonstrations or model-generated labels as independent evidence.
- Checkpoint at meaningful milestones: code/artifact hashes, commands, tests, costs (including zero), findings, next step. Commit/push scoped work to the lane branch without force. Do not merge into main.
- A repo file such as `docs/overnight/<lane>/STATUS.md` is the durable handoff. No need to repeatedly interrupt other chats. These prompts do not authorize contacting teammates through Slack/email.
- Freeze one comparison before any future paid personalized run. Apply the same allowance and judging to every arm. The 10-turn and 30-turn baselines are not an intervention comparison.
- Stop when the lane's acceptance criteria are met or only a real decision/access/spending blocker remains. Breadth comes from distinct useful deliverables, not endless expansion.

The main chat will not invent Gio's critique. A user-approved revision is a later milestone. Overnight workers can prepare useful candidates and evidence without claiming that Gio endorses them.
