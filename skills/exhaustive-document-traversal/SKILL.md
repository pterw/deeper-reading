---
name: exhaustive-document-traversal
description: Use when a long or dense source must be read completely and early retrieval would risk skipped sections, caveats, proofs, appendices, or overrides.
---

# Exhaustive Document Traversal

## Invariant

Chunking is the ruler; exhaustive traversal is the product. **Every canonical chunk** emitted from the bound source must receive exactly one verified `evidence` or explicit `non_match` verdict before completion.

## Required behavior

- Bind the source bytes and produce the canonical chunk universe with the bundled extractor.
- Traverse chunks in canonical order unless a documented recovery changes only the failed unit.
- For `evidence`, record atomic extractive assertions or constraints with source spans.
- For `non_match`, record an explicit reason showing the chunk was inspected.
- Emit one `chunk_verified` event for each canonical chunk.
- A useful finding in an early chunk never authorizes a premature exit.
- Do not replace the evidence ledger with a high-level or abstractive summary.

## Completion gate

Completion is impossible until source re-extraction reproduces the same canonical chunk universe and the evidence ledger covers it exactly.
