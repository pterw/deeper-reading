---
name: verifying-exhaustive-traversal
description: Use when all planned document traversal nodes are resolved and completion must be proven from fresh source bytes, canonical chunk coverage, and reproducible evidence.
---

# Verifying Exhaustive Traversal

## Invariant

`done` is reachable only after fresh verification reproduces the canonical source traversal and proves every required predicate from current bytes.

## Final verification

1. Re-extract the original bound source with the bundled extractor.
2. Reproduce the canonical chunk universe and require exact equality with the run manifest.
3. Require exactly one valid evidence or explicit `non_match` record for every canonical chunk.
4. Require ordered `chunk_verified` coverage for the full canonical universe.
5. Regenerate `TRAVERSAL_REPORT.md` from the canonical manifest and machine evidence and require reproducibility.
6. Verify source fidelity, run-root containment, required format/visual QA, plan resolution, failure/recovery ordering, and requested deliverables.
7. Record `verification_started`, then `verification_passed` only after all fresh checks succeed.
8. Emit `done` only after `verification_passed`, with no later material event.

Old, partial, self-reported, or summary-level evidence is not completion proof.
