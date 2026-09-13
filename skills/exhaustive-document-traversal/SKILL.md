---
name: exhaustive-document-traversal
description: Use when a long or dense source must be read completely and early retrieval would risk skipped sections, caveats, proofs, appendices, or overrides.
---

# Exhaustive Document Traversal

## Invariant

Chunking is the ruler; exhaustive traversal is the product. **Every canonical chunk** emitted from the bound source must receive exactly one verified `evidence` or explicit `non_match` verdict before completion.

## Phase inputs

### Activation and contract establishment

Before establishing the traversal contract, read
[`prerequisites`](../../references/prerequisites.md),
[`runtime-profiles`](../../references/runtime-profiles.md), and
[`control-flow`](../../references/control-flow.md).

### Source acquisition and extraction

Before acquiring or extracting source bytes, read
[`source-acquisition`](../../references/source-acquisition.md) and
[`dependencies`](../../references/dependencies.md). Then load exactly the route
for the selected format:

- PDF: read [`pdf`](../../references/pdf.md), then run
  `python ../../scripts/extract_pdf.py --help` before first use.
- DOCX: read [`docx`](../../references/docx.md), then run
  `python ../../scripts/extract_docx.py --help` before first use.
- HTML: read [`html`](../../references/html.md), then run
  `python ../../scripts/extract_html.py --help` before first use.
- Markdown: run `python ../../scripts/extract_markdown.py --help` before first
  use; read [`lengthy-markdown`](../../references/lengthy-markdown.md) only for large Markdown.

Do not read an unselected format guide.

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
