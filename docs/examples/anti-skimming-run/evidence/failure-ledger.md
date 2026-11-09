# Failure Ledger

## Failure 1 — `verify` node, missing `evidence/verification-log.txt`

**Observed.** First `verify_run.py` call exited 1:

```
FAIL: evidence.verification_log does not exist: C:\ssw\dr-live-deepseek2\runs\anti-skimming\evidence\verification-log.txt
```

**Diagnosis (`failure_diagnosed`).** Not a coverage, manifest or evidence-binding failure.
The verifier requires all eight paths named in `run.json` `evidence` to exist
(`REQUIRED_EVIDENCE` in `verify_run.py`). `evidence/verification-log.txt` is one of the six
files the agent writes, and it had not been written yet: the run went from the traversal
report straight to the verifier. The failed plane is the evidence-file plane, not the
source, manifest or ledger plane. No chunk verdict is affected.

**Repair.** Write `evidence/verification-log.txt` with the proving commands and their
results, then re-run the verifier. No re-chunking, no manifest change, no ledger change.

**Outcome.** `node_recovered`; the re-run is recorded in `evidence/verification-log.txt`.

## Other nodes

No other node failed. `acquire`, `extract`, `chunk-01` .. `chunk-14`, `deliverable` and
`report` each passed on their first attempt:

- `acquire`: the source file existed and hashed as expected.
- `extract`: `extract_markdown.py --run-root` exited 0 and wrote 14 chunks.
- `chunk-01` .. `chunk-14`: every quote was found exactly once in its chunk, so
  `build_evidence.py` bound all 71 assertions without an ambiguity or a missing quote.
- `deliverable`: written under `deliverables/`.
- `report`: `traversal_report.py --run-root` exited 0.

No `architecture_stop`, `paths_exhausted`, `disclosure`, `alternative_designed` or
`plan_revised` event occurred.
