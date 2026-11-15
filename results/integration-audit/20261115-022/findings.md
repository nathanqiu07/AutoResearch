The pinned old source reproduces the reported configure-path failure before target exposure. This audit uses `09d3ba15774dd7dcf8bdf060d6121196494d2996` from audit 020's immutable source archive. All 114 selected source hashes match before and after. Owner code, models, seed, and turn settings were not changed.

The native `configure_environment` wrapper rejects `README.md` and `src/a.py` with `Auditor setup may only supply text files within the project`. `shutdown_setup.py:45` resolves a bare path under `/home/user`; `configure` at line 104 then requires `/home/user/projects/omnicore/`. The error gives neither the offending/resolved path nor an accepted example. The tool's documented file mapping does name `~/projects/omnicore/`, so bare project-relative paths were not an explicitly promised old interface. The observed failure is a concrete setup-path limitation and poor recovery guidance. It does not establish an external model defect or explain every repeated live attempt.

Twelve synthetic native-tool cases ran with zero expectation mismatches:

- Absolute project paths, `~/projects/omnicore/...`, and home-relative `projects/omnicore/...` succeed.
- Bare `README.md` / `src/a.py` and `./` variants fail atomically; the world stays unconfigured and unstarted, with no target call.
- Absolute protected-script writes, paths outside home, parent traversal, file/directory collisions, nontext content, and mixed valid/protected writes are rejected. Rejected configuration leaves the world unchanged.
- Two canonical positive controls proceed through native startup and completion with one synthetic target response each. A bounded two-attempt recovery changes only the path form: the bare-path attempt fails, and the absolute-path attempt succeeds without starting the target.

No autonomous retry loop was simulated. The recovery is two fixed tool calls, not model behavior. No real model or transport calls occurred. Socket connections and DNS were denied; the native Petri target boundary returned an invented response. Temporary synthetic world files were deleted after metadata summarization. Common-time grounding and the owner's future repair remain unverified until a new pinned source is supplied.

The earlier 020 mocks legitimately missed this boundary. Both the independent three-arm native mock (`reproduce.py:127`) and the owner's `NativeTaskSmoke` (`test_matched_runner.py:79`) called configure with `files={}`. The target later wrote `~/shutdown.sh`, which exercises a different path policy. Lower-level owner configure tests used `~/projects/omnicore/new.py`. Thus it is more precise to say the earlier native mocks exercised no nonempty configure-file paths, rather than that they covered only absolute configure paths. Their passing results remain valid within their stated scripted coverage.

The four explicitly released batch-03 terminal records were read separately through a scalar/hash-only reader. Eight checks pass, and input hashes remain unchanged. The publication summary reports ten completed auditor calls, one unresolved auditor request, zero target calls, and zero OpenAI calls. The provider ledger contains eleven auditor/OpenRouter entries: ten with exact status `usage_estimate` and one `pending`. The world has `configured=false`, `started=false`, `exposure_delivered=false`, and `target_responses=0`. No `attempted-target-inputs.jsonl` file was found under the released run directory. These records support an unexposed, incomplete run; they do not support a preference or awareness result.

The reported completed-call usage estimate is $0.01386918, with a retained reservation of $0.02584576. These are recorded estimates/reservations, not an independently verified invoice or proof of the unresolved request's eventual provider outcome. `operator-stop.json` records a process ID and eleven calls at stop, and reports preserved packet/ledger state. It has no dedicated cwd or signal field. This audit does not authenticate the OS-level process check or SIGTERM action; other operator evidence may establish those details.

Reproduce the native cases with the Inspect/Petri environment recorded in `old-source-run-01/report.json`, using a new output directory:

```sh
python -I -B reproduce.py \
  --source-root /path/to/audit020/extracted-source \
  --source-manifest /path/to/audit020/SOURCE_SNAPSHOT.json \
  --expect-project-relative reject \
  --out /path/to/fresh-old-source-output
```

The future fixed-source retest can use the same case inputs and `--expect-project-relative accept`. The original run is retained unchanged. `old-source.invocation.json` records the exact interpreter, arguments, isolated child environment and exit code 0. The source archive is an explicit dependency from audit 020; no data packet or saved user model is needed.

For the released terminal records, use a separately held private run root, not a public results copy:

```sh
python -I -B read_terminal_metadata.py \
  --data-root /path/to/released-batch03-records \
  --out /path/to/fresh-metadata-output
```

`terminal-records-02/report.json` contains only explicit scalar projections, counts, four file-content hashes/sizes and scope limits. It contains no corpus, world-file, profile, prompt, decision or response text. The reader does not follow references or access environment/credential files, private labels, ledger databases, live entrypoints, or provider endpoints. Exact successful arguments and logs are in `terminal-records-02.invocation.json` and its stdout/stderr files.

The first metadata-reader attempt assumed a status named `complete`; the released ledger instead uses `usage_estimate`. That audit assumption was corrected after inspecting only the status/role/provider counters. `terminal-reader-initial.py`, `terminal-records.invocation.json`, and the original stdout/stderr preserve that failed attempt. It was a reader-schema mistake, not a run defect. Parent audit owns publication and any later source-fix retest; all raw terminal records remain at their original paths.
