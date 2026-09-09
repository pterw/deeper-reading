---
name: planning-document-traversal
description: Use when exhaustive document work has multiple acquisition, extraction, traversal, comparison, recovery, or verification steps that need explicit ordering before execution.
---

# Planning Document Traversal

## Invariant

Write a **traversal plan** before substantial multi-step work. The plan exists to make exhaustive coverage and failure boundaries explicit, not to summarize the source.

## Plan shape

Decompose the task as `Task -> Batch -> Chunk -> Operation`. Every node must be bounded and independently verifiable. Typical nodes are source acquisition, format inspection, extraction, canonical chunk creation, chunk traversal, comparison, deliverable production, and final verification.

For each node record:
- exact input and output;
- success evidence;
- failure boundary;
- dependencies;
- whether it can change source authority, fidelity, or task semantics.

Do not plan around “find the relevant section.” Plan around complete traversal of the canonical chunk universe.

## Gate

Execution starts only after the written plan identifies all required traversal and verification nodes.
