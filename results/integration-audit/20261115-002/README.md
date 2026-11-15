# Preserved failed synthetic fixture check

Both audit commands exited 1 because the handcrafted M1 artifact used an empty
config. Its actual constructor adds the default `k: "all"`, so exact serialized
config equality fails. All other roundtrip fields, direct/team request checks,
and 48 backend identity guards passed. This is fixture normalization, not a
detected failure of a normally serialized production artifact.

The inputs are deliberately synthetic canaries with personal fields populated
across methods. They are not fitted profiles or legitimate experimental arms.
No model was called. The exact fixture bytes, tool snapshot, source hashes,
commands, return codes and observations are retained. Re-run using the saved
tool and fixtures with a fresh output path. Package 003 repeats the check using
the actual constructors and serializer, preserving the default config.

The source commits are recorded independently in each observation; CODE_VERSION
identifies the main-derived checkout. No evidence in this package measures
preference accuracy, real confidence, or live backend compatibility.
