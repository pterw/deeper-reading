---
name: debugging-document-workflows
description: Use when a document-workflow node fails, produces unexpected output, or cannot prove its success boundary before any sibling or fallback traversal continues.
---

# Debugging Document Workflows

## Invariant

A failed node must produce `failure_diagnosed` **before** repair, re-chunking, sibling traversal, fallback traversal, or downstream work.

## Phase inputs

After a node fails and before diagnosis or repair, read
[`failure-recovery`](../../references/failure-recovery.md).

## Diagnosis

Record the failed node, exact operation, observed error/output, affected source/chunk, and the smallest evidenced root cause. Compare against a known-good neighboring node or the governing format contract when useful.

Do not fix by changing multiple variables at once. Test one hypothesis at the failed boundary. Preserve already-verified upstream work.

## Allowed transitions after diagnosis

Only after `failure_diagnosed` may execution choose one of:
- `node_rechunked` when scope/size is the diagnosed cause;
- `node_recovered` after a semantics-preserving repair;
- a documented sibling/fallback branch;
- `architecture_stop` when repeated failures show the current path is not viable.

Never broad-retry completed chunks merely because one chunk failed.
