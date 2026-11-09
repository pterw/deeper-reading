---
name: recovering-document-workflows
description: Use when diagnosed recovery branches are exhausted or an architecture stop requires a disclosed alternative path and revised traversal plan before execution can resume.
---

# Recovering Document Workflows

## Invariant

Recovery redesign is a terminal branch of diagnosis, not the first fallback. `alternative_designed` is allowed only after `paths_exhausted` and `disclosure`.

## Phase inputs

Before alternative design or plan revision, re-check
[`failure-recovery`](../../references/failure-recovery.md).

## Exhausted-path sequence

1. Enter `architecture_stop` when the current path is no longer viable.
2. Record `paths_exhausted` after documented semantics-preserving recovery branches have been tried and verified.
3. Produce `disclosure` containing the failed node, root cause, attempted branches, upstream work still valid, unverified remainder, and any source/fidelity/task-semantic consequences.
4. Create `alternative_designed`.
5. Write `plan_revised` before execution resumes.

Do not attempt a fourth repair after an architecture stop without this redesign sequence. Do not silently change source authority, fidelity, or requested semantics to escape a blocker.
