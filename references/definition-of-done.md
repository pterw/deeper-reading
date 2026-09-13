# Definition of Done

Definition of Done is a **predicate set**, not a narrative impression.

A run is DONE only when every required predicate below has fresh evidence.

## Required predicates

| Predicate | Proof required |
|---|---|
| Source identity is established | `evidence/source-manifest.md` records URI/file identity, format, authority, and version/date when material. |
| Skill preflight is complete | `evidence/skill-preflight.md` records `skill_read`, `required_references_read`, `helper_help_read`, `runtime_profile_resolved`, and `traversal_plan_ready`, plus complete phase receipts (a `Reference path` / `Required gate` / `Completed` row) for every reference selected by the actual path; `run.json` references the current preflight state. |
| Plan exists and is resolved | `<run-root>/plan.md` exists; every required plan node is completed or explicitly superseded by an approved revised plan. |
| Output containment is valid | Every emitted machine artifact resolves under `<run-root>/evidence/`, every generated user file resolves under `<run-root>/deliverables/`, the traversal report is `deliverables/TRAVERSAL_REPORT.md`, and `run.json`/`plan.md`/`dod.json` occupy their canonical root paths. |
| Source coverage is complete | The **extractor manifest is the authoritative coverage universe**. Every emitted chunk has **exactly one** bound entry in `evidence/chunk-evidence.json`: atomic extractive assertions/constraints bound to exact chunk bytes, or explicit `non_match` with a reason. |
| Failure protocol was respected | `evidence/failure-ledger.md` shows every failed node produced `failure_diagnosed` before sibling/fallback/downstream traversal. |
| Re-chunking was local | Any size/scope retry is a child of the failed unit; verified upstream chunks were not broadly rerun without reason. |
| Recovery redesign ordering was respected | Any `alternative_designed` event follows `architecture_stop`, `paths_exhausted`, and `disclosure`, and execution resumes only after `plan_revised`. |
| Source fidelity is preserved | No undisclosed substitution of primary/secondary source, original/derivative artifact, or requested task semantics occurred. |
| Format QA is complete | Required live HTML/PDF/DOCX visual/structural checks passed for the operations actually performed and are recorded under `evidence/`. |
| Requested deliverable exists | The exact requested result is produced **and** deterministic `deliverables/TRAVERSAL_REPORT.md` exists as the user-visible traversal proof. |
| No unresolved required failure remains | Failure ledger has zero unresolved required nodes; disclosed optional limitations are marked non-blocking only when they do not violate the request. |
| Final verification is fresh | `verification-before-completion` is invoked after the last material change; `evidence/verification-log.txt` records the fresh proving commands/actions and their results. |
| Machine verifier passes | `scripts/verify_run.py <run-root>/run.json` exits 0 and writes canonical `<run-root>/dod.json` on the current evidence. |

## Anti-skimming completion gate

Chunking is not the deliverable. It is the mechanism that makes exhaustive traversal machine-checkable.

The extractor manifest at `evidence/chunk-manifest.json` defines the complete emitted chunk set. A run may not redefine that universe to only the chunks that looked relevant. `scripts/verify_run.py` binds the source bytes, manifest bytes, chunk hashes/offsets, and `evidence/chunk-evidence.json`, then rejects completion unless every emitted chunk has exactly one evidence verdict.

A high-level summary is never evidence of traversal. Assertions/constraints must be exact byte-anchored source spans, not abstractive paraphrases. If extraction yields 12 chunks, all 12 ledger verdicts **and all 12 discrete `chunk_verified` events** are required; `done` at chunk 4 is premature even when the answer has already been found.

The supplied manifest is not trusted as ground truth merely because it is self-consistent. Final verification re-runs the bundled extractor against the bound source bytes and requires the reproduced canonical chunk universe to match. `deliverables/TRAVERSAL_REPORT.md` is then deterministically regenerated from that canonical manifest + evidence ledger and must match byte-for-byte.

## Output containment gate

The run root is the proof boundary. Original inputs may live outside it; emitted artifacts may not.

If a requested generated file, machine evidence file, traversal report, or final DoD artifact is emitted outside its canonical run-root namespace, the run is **NOT DONE** even if the file itself exists. Scattered output cannot satisfy completion predicates because it is not bound to the auditable run workspace.

Verifier-only temporary re-extraction scratch is exempt only because it is ephemeral, automatically cleaned, and cannot satisfy any evidence predicate.

## Terminal equation

```text
DONE =
  source_identity_verified
  AND skill_preflight_complete
  AND plan_resolved
  AND output_containment_valid
  AND extractor_manifest_coverage_complete
  AND failure_protocol_respected
  AND source_fidelity_preserved
  AND format_qa_complete
  AND requested_deliverable_produced
  AND deterministic_traversal_report_matches
  AND discrete_chunk_verifications_complete
  AND unresolved_required_failures == 0
  AND fresh_final_verification_passes
  AND machine_verifier_exit_code == 0
```

If any required predicate is false or unproved, the state is **NOT DONE**.

## Freshness rule

Evidence created before the last material change is stale for completion purposes. Re-run the proving check after the last source, plan, deliverable, script, or workflow change that could affect the predicate.

Do not infer completion from:

- file existence alone;
- an earlier successful run;
- an agent saying it finished;
- a partial source read;
- a clean derivative render;
- tests unrelated to the failed requirement.

## Partial completion

If the user accepts a reduced scope after disclosure, update the written plan and requested-deliverable contract first. Then recompute DoD against the **approved revised scope**. Do not retroactively label an unapproved partial result complete.
