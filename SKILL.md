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

## Required package-owned skills

Read the applicable module in full before that phase:

- `skills/exhaustive-document-traversal/SKILL.md`
- `skills/planning-document-traversal/SKILL.md`
- `skills/executing-document-traversal/SKILL.md`
- `skills/debugging-document-workflows/SKILL.md`
- `skills/recovering-document-workflows/SKILL.md`
- `skills/verifying-exhaustive-traversal/SKILL.md`

## Required references

Read these in full when this skill activates: `references/prerequisites.md`, `references/runtime-profiles.md`, `references/control-flow.md`, `references/dependencies.md`, `references/source-acquisition.md`, `references/deliverable.md`, `references/evidence.md`, `references/definition-of-done.md`, `references/failure-recovery.md`, `references/anti-patterns.md`, plus the applicable format reference and `references/lengthy-markdown.md` for large Markdown.

## Execution invariants

- Decompose as `Task -> Batch -> Chunk -> Operation`.
- One shell/container call contains one simple operational command.
- On failure, emit `failure_diagnosed` before sibling/fallback/downstream traversal.
- Re-chunk only the failed unit when scope/size is the diagnosed cause.
- After `architecture_stop`, do not continue repairs until `paths_exhausted -> disclosure -> alternative_designed -> plan_revised`.
- Preserve source authority, task semantics, already-verified upstream work, and the canonical anti-skimming chunk universe.
- `oai-native` may add rendering/OCR/visual QA, but may never weaken or replace the standalone evidence contract.

## Definition of Done

Done requires the exact requested deliverable, a complete atomic evidence ledger for every canonical chunk, deterministic `TRAVERSAL_REPORT.md`, resolved failure/recovery ordering, required format QA, fresh verification after the last material event, and `scripts/verify_run.py` exit 0 on current evidence.

A useful answer found early is never permission to stop traversal.