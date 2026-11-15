# Frozen pricing arithmetic test correction

The integration failure was in one test fixture, not the reservation calculation. The Role09
historical checkout had base input rates0.10/2/10 USD per million, while frozen f6 uses the
conservative1.25× 30-minute cache-write input rates0.125/2.5/12.5. Output rates remain0.50/10/50.
The test incorrectly expected the historical base-rate arithmetic.

The single test now names frozen cache-write pricing and temporarily supplies the declared f6
rate table through `patch.object`. For1000 input and200 output units, the expected bounds are
$0.000225, $0.0045 and $0.0225 for Luna, Sol and Astra. The fixture is independent of the checkout's
historical rate table. Independent review ran the two reservation tests and verified that the
same original rate object and values are restored afterward. No backend, rate table, helper,
wire body, runtime, request settings or reservation formula changed.

A separate zero-call verification imported the backend from the exact frozen f6 path and checked
its file SHA256 `6ece37e0a623e8d0a7e3b916925532d1c239a0a82269d98cc2d40fb8563a232d`.
It loaded the unchanged helper SHA256
`740f4517d67379af5bc75d772495114599c58dc83424e4c164b0605ec2b9dcad` and the published safe report
`ec31be71a741cfe4c986ff5f0183a3f7c6045418aef69ba9ee25c7ac382c2b94`.
All476 prediction reservations and the build reservations were recalculated using actual f6
rates. Ready maxima$77.253780112 plus future maxima$141.848819000 reproduce the unchanged
**$219.102599112** total. Thus the published plan used the correct higher rates; the stale test
expectations did not reduce the proposed ceilings. These remain conservative maxima, not actual
spend or permission to exceed the coordinator's$80 spend-plus-holds limit.

Validation:83 scaling tests pass; full suite892 tests,890 passed and2 skipped,25.769s. Independent
review found no issue with the narrow test change. No private payloads, labels, provider calls or
live ledger were accessed. The separate request-hash convention clarification in handoff0007
continues to apply; this test fix provides no admission clearance.
