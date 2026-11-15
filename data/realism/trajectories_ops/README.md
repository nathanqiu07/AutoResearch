# Business-ops agent trajectories (non-coding)

Public tool-using agent sessions for customer service (airline, retail, telecom), email,
calendar, banking, travel and finance, plus real user chats about business tasks. They ground
Petri audit seeds about business-ops agents, the way `../trajectories/` does for coding agents.
Collected 2026-11-15 from GitHub (`gh`, raw.githubusercontent.com) and the HF datasets-server
`/rows` API. No gated datasets were used.

## Format

One JSONL line per trajectory, same shape as `../trajectories/` plus `domain` and `tools`:

```
{"source", "license", "id", "domain", "task", "turns": [{"role", "content", "tool_calls"?, "name"?, "tool_call_id"?}], "tools", ...extra metadata}
```

- `domain` is one of email | calendar | retail | airline | banking | travel | support | finance | data | other.
- `task` is the content of the first `user` turn, verbatim.
- Roles are `system`, `user`, `assistant`, `tool`. `tool_calls` entries are `{"id"?, "name", "arguments"}`
  with `arguments` a JSON string (ToolBench: the raw `Action Input` text).
- `tools` is the tool schema list the agent was given, or `null` when the source has none.
- Message content is verbatim. Any `content` or tool-call `arguments` string over 20,000 characters
  is cut to 20,000 and followed by `[truncated N chars]`.
- Email addresses are replaced by `user@example.com` only in sources with real data (WildChat user
  chats, ToolBench's live API responses), on parsed string values. The benchmark environments'
  synthetic names, emails, IBANs and IDs are left as they are.
- Rows the datasets-server returned with truncated cells were skipped.

## Sources

| File | Source | License | Count | Domains | Selection rule | Field mapping | Users |
|---|---|---|---|---|---|---|---|
| `tau_bench.jsonl` | [sierra-research/tau-bench](https://github.com/sierra-research/tau-bench) `historical_trajectories/gpt-4o-{airline,retail}.json` | MIT (repo) | 50 (26 reward 1 / 24 reward 0) | airline 25, retail 25 | Per domain: shuffle task ids (seed 0), one trial per task, alternating success/failure | `traj[]` OpenAI messages; `tool_calls[].function` -> `name`/`arguments`; tool turns keep `name`, `tool_call_id`. First turn is the domain policy (system). Extra: `model` gpt-4o, `reward`, `user_instruction` (the simulator's hidden scenario). `tools` from each tool class's `get_info()` in `tau_bench/envs/<domain>/tools/` | Simulated (gpt-4o user simulator) |
| `tau2_bench.jsonl` | [sierra-research/tau2-bench](https://github.com/sierra-research/tau2-bench) `data/tau2/results/final/claude-3-7-sonnet-20250219_{airline,retail,telecom}_default_gpt-4.1-2025-04-14_4trials.json` | MIT (repo) | 50 (31 / 19) | airline 17, retail 17, support 16 (telecom tech support and billing) | Same rule as tau-bench | `simulations[].messages[]`; `tool_calls[]` `name`/`arguments`; tool turns keep `tool_call_id` (= message `id`) and `requestor`. A `system` turn holding `info.environment_info.policy` is prepended (the agent's prompt wrapper is not stored). Telecom has user-side tool calls (role `user` with `tool_calls`, simulating the customer's phone), kept as is. Extra: `reward`, `termination_reason`, `tau2_domain`, `user_instruction`. `tools` built from `@is_tool` methods in `src/tau2/domains/<domain>/tools.py` (name, docstring, annotated parameters) on today's `main`; may differ slightly from the June 2025 run's commit. User-side telecom tools are not listed | Simulated (gpt-4.1 user simulator) |
| `agentdojo.jsonl` | [ethz-spylab/agentdojo](https://github.com/ethz-spylab/agentdojo) `runs/gpt-4o-2024-05-13/` | MIT (repo) | 50: 40 benign, 10 with prompt injection | email 6, calendar 9, banking 11, travel 11, other 13 (cloud-drive files and Slack) | Benign: `user_task_*/none/none.json`, shuffled (seed 0), workspace 16, travel 9, banking 8, slack 7. Injected: `important_instructions` attack runs, workspace 3, travel 2, banking 3, slack 2, half where the injection succeeded | `messages[]`; `tool_calls[].function`/`args` -> `name`/`arguments`; tool turns keep `tool_call_id`, `name`, `error`. Workspace domain set by tools used (email > calendar > other). Extra: `suite`, `utility`, `injected`; for injected runs `attack_type`, `injection_task_id`, `injections` (the injected text by placeholder) and `injection_succeeded` (AgentDojo's `security` flag, True = the attacker's goal was met). `tools` built from the suite's `TOOLS` list in `src/agentdojo/default_suites/v1/` (environment-injected `Depends` parameters dropped) | No user simulator: one scripted user instruction, then the agent works alone |
| `apigen_mt_5k.jsonl` | [Salesforce/APIGen-MT-5k](https://huggingface.co/datasets/Salesforce/APIGen-MT-5k) | cc-by-nc-4.0 (non-commercial) | 50 | airline 25, retail 25 | 8 random pages of 100 (seed 0); domain from the tool list (`book_reservation` -> airline); 25 per domain at random | `conversations[]`: `human` -> user, `gpt` -> assistant, `function_call` -> assistant with one tool call, `observation` -> tool; row `system` (tau-bench policy) as first turn; `tools` parsed from the row | Simulated (LLM human in the APIGen-MT pipeline, tau-bench environments) |
| `toolbench.jsonl` | [tuandunghcmut/toolbench-v1](https://huggingface.co/datasets/tuandunghcmut/toolbench-v1), a mirror of [OpenBMB/ToolBench](https://github.com/OpenBMB/ToolBench) | apache-2.0 | 48 | finance 10, retail 8, email 8, travel 8, data 6, banking 4, calendar 4 | 89 random pages of the train split; dropped DFSDT retry rows ("This is not the first time you try this task") and rows with fewer than 2 tool results; domain = the single domain all called tool names map to by keyword, else dropped; per-domain quotas | `conversations.from/value`: `function` -> tool. Classic ReAct: assistant `content` keeps the inline `Thought/Action/Action Input` text, and `tool_calls` holds the parsed last `Action`. `tools` parsed from the system prompt's API list. Domain labels are keyword-based and noisy (RapidAPI tools such as email validators, game-item prices, F1 schedules) | Generated queries (ChatGPT-written), real RapidAPI responses |
| `wildchat_business.jsonl` | [allenai/WildChat-1M](https://huggingface.co/datasets/allenai/WildChat-1M) | odc-by | 50 | email 24, data 10, finance 8, support 4, retail 4 | 217 random pages of 100 rows (seed 0). Kept non-toxic chats whose first user message is English, at least 80 chars, not a role-play prompt (`act as`, `pretend`...), and whose first 300 chars match a business-task pattern (write/reply to an email, customer reply, invoice or financial statement, Excel/spreadsheet, refund or order); first matching domain wins; per-domain quotas. Regex-picked, so a few are borderline (a marketplace ad, an exam question about Excel). No calendar matches survived | `conversation[]` -> `role`/`content` only (IP hashes, headers, location dropped). Extra: `model` (ChatGPT model), `timestamp`. `tools` null: these are plain chats, not tool use | Real users (WildChat already replaces names with `<PRESIDIO_ANONYMIZED_PERSON>`; emails masked here) |

Sizes: tau_bench.jsonl 1.48 MB; tau2_bench.jsonl 1.95 MB; agentdojo.jsonl 0.73 MB; apigen_mt_5k.jsonl 1.24 MB; toolbench.jsonl 0.71 MB; wildchat_business.jsonl 0.26 MB. Every line was parsed and checked for the required fields.

## Skipped

- **LMSYS-Chat-1M** and **Salesforce/xlam-function-calling-60k**: gated (terms must be accepted). xLAM-60k is single-turn anyway.
- **Team-ACE/ToolACE** (apache-2.0): only about 2.5% of rows (100 of 4,000 sampled) contain tool results; the rest are single function-call outputs. Of those, 4 fell in business domains, too few to keep. Calls are Python-like text (`[Func(a=1)]`) with no structured arguments.
- **Berkeley Function Calling Leaderboard** multi-turn: no HF data files the datasets-server can read; the GitHub data holds questions plus ground-truth call lists with no tool outputs or model turns, so not trajectories.
- **Salesforce/xlam-interaction-trajectories**: not accessible without authentication.
- **WebArena / VisualWebArena**: not attempted; traces are browser accessibility trees, large and not tool-call shaped.
- tau-bench's `sonnet-35-new-*` trajectories: not used because the assistant content repeats each call as inline `<function_calls>` XML next to the structured call; gpt-4o runs are cleaner.

## Caveats

- `wildchat_business` holds real people's chats. Names were anonymized by WildChat; emails were masked here; company names, order numbers and other details remain. Treat with care if excerpts are shown to anyone.
- `toolbench` responses come from live third-party APIs in 2023 and can contain real-world data.
- `apigen_mt_5k` is non-commercial (CC-BY-NC-4.0).
- AgentDojo injected runs contain attack text by design; check `injected` before using a run as a benign example.
