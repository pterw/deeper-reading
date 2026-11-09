---
name: deeper-reading
description: Use when long or dense documents must be read exhaustively and models are at risk of skimming, stopping at the first plausible match, or claiming completion before every source chunk is verified.
compatibility: standalone is the default profile with bundled extractors and package-owned document workflow skills; optional oai-native enhancements may add richer visual/OCR QA without changing the anti-skimming evidence contract.
---

# Deeper Reading: Exhaustive Document Traversal

## Core rule

The primary mission is **exhaustive traversal**: read the complete source and prove coverage before Done. **Chunking is the mechanism** that prevents a first-plausible-match exit. Every emitted chunk in the canonical manifest must receive exactly one verified `evidence` or explicit `non_match` verdict.

## Quick path

```text
START
  -> exhaustive-document-traversal
  -> resolve runtime/document profile
  -> planning-document-traversal -> written traversal plan
  -> executing-document-traversal -> one bounded node at a time
       PASS -> prove node -> next node
       FAIL -> debugging-document-workflows -> failure_diagnosed
                 -> local repair/re-chunk OR architecture_stop
                 -> recovering-document-workflows when paths are exhausted
  -> all canonical chunks + required plan nodes resolved
  -> verifying-exhaustive-traversal -> fresh source re-extraction
  -> scripts/verify_run.py PASS
  -> DEFINITION OF DONE
```

`standalone` is the canonical/default runtime profile. `oai-native` is an optional enhancement profile only.

The **run root is the output and proof boundary**: source manifests, chunk evidence, traversal proof, requested deliverables, and verification evidence must resolve inside that run namespace.

## Phase-gated loading

The root owns lifecycle order. Read the bundled module for the current state in
full; that module owns the references and helper guidance required before its
gate. Do not preload modules for states that have not been reached.

| Current lifecycle state | Bundled module |
|---|---|
| Enter and establish the contract | `skills/exhaustive-document-traversal/SKILL.md` |
| Write the traversal plan | `skills/planning-document-traversal/SKILL.md` |
| Acquire and extract the selected format | Reuse `skills/exhaustive-document-traversal/SKILL.md` and load its selected-format inputs |
| Execute bounded traversal nodes | `skills/executing-document-traversal/SKILL.md` |
| Diagnose a failed node | `skills/debugging-document-workflows/SKILL.md` |
| Redesign after exhausted recovery paths | `skills/recovering-document-workflows/SKILL.md` |
| Prove final completion | `skills/verifying-exhaustive-traversal/SKILL.md` |

Return to this table only when the lifecycle state changes. A module may
require a later module after its own transition succeeds; it may not move a
later module or reference earlier.

## Execution invariants

- Decompose as `Task -> Batch -> Chunk -> Operation`.
- One shell/container call contains one simple operational command.
- On failure, emit `failure_diagnosed` before sibling/fallback/downstream traversal.
- Re-chunk only the failed unit when scope/size is the diagnosed cause.
- After `architecture_stop`, do not continue repairs until `paths_exhausted -> disclosure -> alternative_designed -> plan_revised`.
- Preserve source authority, task semantics, already-verified upstream work, and the canonical anti-skimming chunk universe.
- Treat evidence construction as byte binding, not summary generation: schema v2 `atom_id` values identify verified extractive spans, while schema v1 remains accepted.
- Prefer the grouped deterministic `TRAVERSAL_REPORT.md` and bounded `scripts/inspect_chunks.py` view for **human audit**; neither replaces the machine evidence ledger.
- Machine verification proves source identity, canonical coverage, byte fidelity, ordering, and declared workflow predicates. It does **not** prove semantic truth or model comprehension.
- `oai-native` may add rendering/OCR/visual QA, but may never weaken or replace the standalone evidence contract.

## Definition of Done

Done requires the exact requested deliverable, a complete atomic evidence ledger for every canonical chunk, deterministic `TRAVERSAL_REPORT.md`, resolved failure/recovery ordering, required format QA, fresh verification after the last material event, and `scripts/verify_run.py` exit 0 on current evidence.

The terminal contracts are `references/deliverable.md`, `references/evidence.md`, and `references/definition-of-done.md`; the last of these is the predicate authority for this gate. Document-dependency resolution is owned by `references/dependencies.md`.

A useful answer found early is never permission to stop traversal.