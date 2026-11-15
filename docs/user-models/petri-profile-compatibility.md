# The new P8 profiles need a separate adapter

The completed Petri comparison used the saved filtered Hobbhahn SynthesizeMe M2 profile. Its adapter expects a written persona, selected preference examples, and learning/validation provenance.

An offline check of the selected Neel Nanda and Chris Olah P8 replicate-0 profiles found a different schema: `neutral-profile-v1`, with hypotheses and relations. The current adapter rejects both. This is a format mismatch, not evidence that either profile is invalid. Packet preparation also pins the original Hobbhahn model bytes.

No profile was converted, no history or weights were invented, and no target or judge saw these P8 profiles. Both source files stayed unchanged. Root independently repeated both rejection checks with network access blocked.

A future comparison would need a separately reviewed renderer for the neutral profile format, preserving its unknowns and source IDs, plus a new packet. That work is outside this closed paid pilot; it was not silently added.

[Exact offline check, profile IDs, source hashes and errors](petri-profile-compatibility.json)
