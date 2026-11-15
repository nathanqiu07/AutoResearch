# Lane06 scenario realism handoff

Use the identical [authoring addition](authoring-addition.txt) across all arms. [Contract](AUTHORING_CONTRACT.md) fixes the scope. The checker accepts the existing `configure_environment(files, workspace_note, entrypoint)` arguments.

```python
from scripts.gio_recovery.scenario_check import check_environment
report = check_environment(files, workspace_note, entrypoint)
# Hard failures reject this setup under the same bounded policy in every arm.
# Review flags go to Lane07; structural pass is never semantic clearance.
```

For saved snapshots, use **world-initial.json only**, never terminal world-state.json. Target actions must not be reclassified as authored-environment defects. The checker returns `unsupported_input_phase` for observed post-target state. `begin()` saves the initial snapshot before delivery; `exposure_delivered=false` is valid there and does not prove the target received the opportunity.

```bash
python3 scripts/gio_recovery/scenario_check.py --world WORLD_INITIAL.json --out NEW_CHECK.json
python3 -m unittest tests.test_gio_recovery_scenario_check -v
```

CLI exits2 on structural failure or unsupported phase;0 means only structural pass, even with review flags. Output creation is exclusive. No generated source is executed. Optional `--expected-facts COMMON.json` compares exact caller-frozen world fields across arms. Models/settings and direct target/judge context isolation are checked by lanes01/07/09.

## Saved failures detected

The unchanged run05 generic initial report is a hard reserved-output violation. All three saved environments produce evidence-located answer-annotation flags. The baseline nested workspace-looking path is a review flag, since that shape can be a legitimate fixture tree. The profile Docker/Python launch is flagged for lacking a recognized entry action. These checks do not imply the target copied an unread report or that no static review opportunity existed. [Diagnostics](saved-world-checks.json).

## Offline fixture

[Coherent environment](fixtures/coherent-environment.json) is a new handwritten plumbing fixture, not a generated/live result. It contains neutral source and an absent target report. Its advertised standard-library CLI runs; a separate controlled local probe confirms a reachable issue. The native simulated world permits script changes, schedule changes, and report writing. [Offline checks](offline-authoring-check.json). Do not feed that verification report into the target context. Use fresh authored worlds for the actual treatment comparison.

All checks cost0 and make0 model calls. The fixed clock, no actual shutdown, forced exposure and unsupported full semantic-realism claim remain explicit. Lane06 does not duplicate Lane07 semantic/outcome scoring or Lane09 dispatch.
