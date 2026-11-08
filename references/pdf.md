# PDF Workflow

## Required document profile

Resolve the document profile first. `standalone` is canonical/default and uses the bundled `scripts/extract_pdf.py` for deterministic text extraction and chunk-universe generation. `oai-native` is an optional enhancement for rendering, OCR, layout, forms, conversion, and other richer PDF mechanics.

Before PDF execution:
1. resolve the profile through `references/runtime-profiles.md`;
2. run `python scripts/extract_pdf.py --help`;
3. verify a declared text backend is available;
4. under `oai-native`, also read the live PDF guidance required by `references/dependencies.md` before using native helpers;
5. read current helper help before first use.

The bundled extractor defines the canonical anti-skimming text chunk universe in every profile. Native helpers may add evidence or QA, but may never replace, shrink, reorder, or redefine that universe.

## Anti-skimming extraction manifest

Use `scripts/extract_pdf.py` to emit page-located text chunks and the authoritative extraction manifest. Every emitted chunk requires exactly one atomic extractive evidence verdict or explicit `non_match`, one `chunk_verified` event, and inclusion in deterministic `TRAVERSAL_REPORT.md` before Done. Empty-text pages remain represented so a page cannot disappear merely because text extraction found nothing.

At final verification, re-extract the original source with the bundled extractor and require exact equality with the run-provided chunk universe. Never trust `chunks.json` as self-authenticating.

## PDF provenance

For a PDF run, copy the extractor manifest's `extraction` object into `run.json`:

```json
{"extraction": {"backend": "pypdf 5.3.0", "format": "pdf", "capabilities": ["text"]}}
```

Use the actual backend and version emitted locally, not the example value.
The `backend` value carries the version, so a run whose `extraction` differs from the manifest's (a different backend or backend version) fails `extraction.manifest.mismatch`; after changing either, re-extract and rebuild the evidence.
The verifier requires this object and compares it with the independently
reproduced manifest. It also requires a known backend (`pypdf`, `pdftotext`,
`pymupdf` or `pdfplumber`), `format` `pdf`, and `capabilities` equal to
`["text"]`, the text adapter's. It rejects any QA check naming OCR, because
Text backends cannot justify an `ocr-verified` QA claim. The record is
included in `dod.json`. Richer QA needs separately recorded evidence from an
approved provider; it is not inferred from a text library's possible
capabilities.

Extraction accepts `--password` for encrypted files, but final verification
re-extracts without a password, so it fails closed rather than storing
credentials in a ledger. Use an explicitly approved decrypted source with its
own identity and fidelity record if final verification is required.

## Visual and structural truth

Standalone extraction proves exhaustive traversal of the extractor-visible text, not figures, equations, tables rendered as graphics, or page layout. If the requested task depends on those features and no approved visual provider is available, the run must disclose the missing capability and cannot claim that visual content was exhaustively verified.

Under `oai-native`, keep the native render-first visual loop:

```text
render bounded source range
  -> inspect every rendered page
  -> structural inspection
  -> compare text extraction with the source render
  -> record format/visual QA evidence
```

The optional native branch supplements the canonical chunk ledger; it never substitutes for it.

## Chunking

Long PDF:
- operate on bounded page ranges;
- if a node fails because scope is too large, record `failure_diagnosed` and split only that failed range;
- never rerun already verified pages because a later range failed.

Multiple papers:
- one paper is its own top-level batch;
- finish exhaustive traversal evidence for one paper before cross-paper synthesis;
- a failure in paper B does not invalidate verified evidence from paper A.

## Conditional native branches

When `oai-native` is selected, use the live PDF guidance to decide when to invoke OCR, preflight/normalization, renderer parity, forms, coordinate extraction, conversion, or batch utilities. Do not invoke expensive or lossy branches by default.

## Source integrity

The source bound into the manifest must be the actual PDF artifact or an explicitly approved faithful conversion. Never render or verify a PDF made from your own notes and treat it as proof that the source was read.

## Failure

At the first failed PDF operation:
- stop the current node;
- record `node_failed`;
- diagnose the failure and record `failure_diagnosed`;
- re-chunk only the failed unit when scope is the cause;
- do not traverse siblings or fallbacks before diagnosis;
- after the documented recovery tree is exhausted, use the package-owned architecture-stop and recovery protocol.
