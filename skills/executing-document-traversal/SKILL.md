---
name: executing-document-traversal
description: Use when a written traversal plan is ready and document nodes must be executed one bounded operation at a time with evidence before advancing.
---

# Executing Document Traversal

## Invariant

Execute **one bounded** plan node at a time. A node advances only after its output is inspected and its proving evidence is recorded.

## Loop

1. Start the smallest unresolved node.
2. Execute one operation with one observable success/failure boundary.
3. Inspect the output.
4. On success, record the node result; for canonical document chunks emit the required `chunk_verified` event only after its evidence ledger record is valid.
5. Continue to the next unresolved node.

If a node **failed**, stop traversal at that boundary. Do not jump to a sibling, fallback, later chunk, or downstream node before the failure-diagnosis gate has been satisfied. Preserve every already-passing node.

## Anti-skimming rule

An early useful answer is not a terminal state. Execution continues until every canonical chunk and every required verification node in the traversal plan is resolved.
