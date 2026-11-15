# Real coding-agent trajectories

Public agent trajectories from Hugging Face, for grounding realistic Petri audit seeds
(real trajectory prefixes lower a model's P(eval)). Collected 2026-11-15 through the
HF datasets-server `/rows` API. No gated datasets were used.

## Format

One JSONL line per trajectory:

```
{"source", "license", "id", "task", "resolved", "turns": [{"role", "content", "tool_calls"?, "name"?}], ...extra metadata}
```

- `task` is the content of the first `user` turn, verbatim (the issue text wrapped in the
  scaffold's own instruction template; for openhands-feedback it is the user's first chat message).
- Message content is verbatim. Any single `content` or tool-call `arguments` string over
  20,000 characters is cut to 20,000 and followed by `[truncated N chars]`.
- `tool_calls` entries are `{"id"?, "name", "arguments"}` with `arguments` a JSON string.
- Rows the datasets-server returned with truncated cells were skipped.

## Sources

| File | Source | License (dataset card) | Count | Selection rule | Field mapping |
|---|---|---|---|---|---|
| `nebius_swe_agent.jsonl` | [nebius/SWE-agent-trajectories](https://huggingface.co/datasets/nebius/SWE-agent-trajectories) | cc-by-4.0 | 50 (17 resolved / 33 unresolved, 50 repos) | Random pages across the 80k-row train split (seed 0); greedy pick alternating resolved/unresolved, one per repo first, at most one per instance | `trajectory[]`: `system_prompt` (system) or `text` (user/ai); `ai` -> `assistant`. Classic SWE-agent: actions are inline in assistant text, observations are `user` turns, no structured tool calls. `resolved` = `target`; extra: `instance_id`, `model`, `exit_status` |
| `nebius_swe_rebench_openhands.jsonl` | [nebius/SWE-rebench-openhands-trajectories](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories) | cc-by-4.0 | 50 (25 / 25, 50 repos) | Same rule over the 67k-row train split | `trajectory[]` OpenAI-format messages; `tool_calls[].function` -> `name`/`arguments`; tool turns keep `name`. `resolved` = `resolved == 1`; extra: `instance_id`, `exit_status` |
| `swe_gym_openhands_sampled.jsonl` | [SWE-Gym/OpenHands-Sampled-Trajectories](https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories) | not stated on the card (the SWE-Gym code repo is MIT) | 50 (10 resolved / 40 unresolved, 10 repos) | Same rule over the 6k-row `train.raw` split. SWE-Gym covers only ~11 repos and most runs are unresolved, so repo spread and resolved share are limited | `messages[]` OpenAI-format, mapped as above. `resolved` = `resolved`; extra: `instance_id`, `model_run` (`run_id`) |
| `swe_smith_trajectories_tool.jsonl` | [SWE-bench/SWE-smith-trajectories](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories) (`tool` split) | mit | 50 (24 / 26, 50 repos) | Same rule over the 24k-row `tool` split | `messages` (JSON string) parsed; list-of-parts `content` joined to text; `tool_calls` mapped as above. Tasks are SWE-smith synthetic bugs written up as PR descriptions. `resolved` = `resolved`; extra: `instance_id`, `model` |
| `openhands_feedback.jsonl` | [OpenHands/openhands-feedback](https://huggingface.co/datasets/OpenHands/openhands-feedback) (was all-hands/openhands-feedback) | mit | 50 | Real user sessions shared publicly via thumbs up/down. All 275 rows read; kept sessions with at least one user message and two tool actions; 25 positive, 25 negative feedback | OpenHands event stream: `message` actions -> `user`/`assistant` by `source`; other actions -> `assistant` turn with `content` = the action's `thought` (else `message`) and one tool call `{name: action, arguments: extras minus thought}`; observations -> `tool` turn (`name` = observation type, `content`). Dropped: initialize/agent-state events, null observations, environment status lines. `resolved` = null; extra: `feedback` |

Resolved share falls short of 50/50 for SWE-agent and SWE-Gym because few resolved runs
turned up in the sampled pages. Sizes: 2.8, 11.8, 2.5, 4.9 and 3.6 MB in table order.

## Caveats

- `openhands_feedback` holds real users' sessions that they chose to publish. A few contain
  personal email addresses and project details; treat it with care if excerpts are shown to anyone.
- `nebius_swe_agent` contains an AWS-style access key id (`AKIA...`) inside repo content seen by
  the agent, most likely a test fixture; kept verbatim.

## Redactions (2026-11-15, by the committing session)

- One AWS-style access key ID in `nebius_swe_agent.jsonl` (repo content the agent saw) replaced with `AKIAXXXXXXXXXXXXXXXX`.
- Personal email addresses in `openhands_feedback.jsonl` replaced with `user@example.com`; noreply and example.* addresses kept.
