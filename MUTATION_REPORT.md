# Hard-Standalone Mutation Report

Date: 2026-09-08

## Method

Each mutation begins from a valid baseline and changes one required state, evidence edge, or workflow transition. A mutation passes only when the package rejects the illegal state for the intended reason.

This is deterministic mutation testing of the executable workflow contract. It is not presented as independent-agent behavioral pressure testing.

## Process mutation suite — 11/11 GREEN

`tests/test_mutations.py` verifies:

| Mutation | Required rejection |
|---|---|
| unmutated baseline | PASS |
| skip required reference read | preflight incomplete |
| skip written traversal plan | `plan_written` missing |
| failed node -> sibling before diagnosis | `failure_diagnosed` required |
| alternative design before architecture stop | redesign gate rejected |
| Done before final verification | verification required |
| unresolved failed node at Done | unresolved failure rejected |
| rechunk/repair before diagnosis | diagnosis-before-repair rejected |
| repair after `architecture_stop` without redesign/replan | architecture stop barrier |
| alternative design before `paths_exhausted` + `disclosure` | recovery ordering rejected |
| later material event after verification | stale final verification rejected |

Observed checkpoint: **11/11**.

## Anti-skimming ledger suite — 19/19 GREEN

`tests/test_anti_skimming_ledger.py` verifies that the extractor manifest, atomic evidence ledger, source bytes, traversal events, and human-readable report agree.

Critical threat models:

### 12 emitted / 4 evidenced

A source that deterministically emits **12 emitted** chunks is mutated so only **4 evidenced** entries remain.

Expected and observed: eight missing-chunk violations; DoD `source_coverage_complete=false`; run rejected.

### Skipped middle chunk

A middle evidence entry is removed while later chunks remain evidenced.

Expected and observed: the **skipped middle** chunk is rejected. Later evidence cannot justify a gap.

### Early Done

The event stream attempts **early Done** without the required final verification cycle.

Expected and observed: Done is rejected.

### Forged smaller manifest

The supplied chunk manifest is rewritten into a self-consistent four-chunk subset; its hash, coverage arrays, and evidence ledger are forged to agree with the smaller universe.

Expected and observed: the run is rejected by **source re-extraction**. `verify_run.py` invokes the bundled extractor against the original source bytes and requires the reproduced canonical manifest to match. A **forged smaller manifest** therefore cannot redefine what "all chunks" means.

### Missing or reordered traversal proof

Every canonical manifest chunk requires one ordered `chunk_verified` event. Missing, duplicate, unknown, or reordered events are rejected.

## Atomic evidence contract

For `outcome: evidence`, assertions/constraints are atomic extractive objects:

```text
text
chunk_byte_start
chunk_byte_end
```

The verifier proves that the cited bytes equal the assertion text exactly.

`outcome: non_match` requires an explicit reason.

Abstractive chunk summaries are not accepted as traversal proof.

## User-visible traversal proof

`TRAVERSAL_REPORT.md` is regenerated deterministically from the canonical manifest and `chunk-evidence.json`.

The verifier rejects a report that does not reproduce exactly, preventing a human-facing report from drifting away from machine evidence.

## Installer mutation suite — 11/11 GREEN

`tests/installer/test_install_mutations.py` starts from a valid standalone installation and rejects:

| Mutation | Predicate |
|---|---|
| unmutated installation | PASS |
| canonical `SKILL.md` nested/missing | `canonical_root=false` |
| manifest-owned reference deleted | `payload_hashes_match=false` |
| standalone document readiness changed to missing | `document_profile_resolved=false` |
| `oai-native` receipt on standalone runtime | runtime/profile consistency false |
| installed payload bytes modified | payload hash false |
| host discovery marked failed | discovery predicate false |
| staging directory left after success | no-staging-leftovers false |
| backup directory left after success | no-backup-leftovers false |
| receipt points at another root | receipt-root identity false |
| receipt deleted | receipt predicate false |

No installer mutation depends on a Superpowers readiness predicate; Task 6 removed that external runtime prerequisite.

## Transaction/ownership fault injections

Separate installer tests prove:

- rollback after post-replace failure;
- rollback after discovery failure;
- dry-run performs no target mutation;
- unmanaged existing target is refused;
- modified managed files are refused on upgrade;
- stale receipt-owned files are pruned when removed from the new payload;
- unowned user files survive upgrade and uninstall;
- modified managed files are not silently removed.

## Result

The package's major early-exit, forged-universe, stale-verification, installer-integrity, and ownership failure modes are represented by executable rejection tests.

Frozen-archive verification must rerun these suites from extracted archive bytes before release completion.
