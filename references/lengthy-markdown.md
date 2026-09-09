# Lengthy Markdown Workflow

Markdown uses the bundled `scripts/extract_markdown.py` extractor to create the exhaustive chunk manifest. Chunking is the mechanism; exhaustive traversal with evidence is the requirement.

## Structural splitting

Split on Markdown heading structure at `# / ## / ###`. Preserve the active heading path in each chunk locator. A heading-looking line inside a fenced code block is content, not a heading.

Treat these structures as **atomic**:

- fenced code blocks using backticks or tildes;
- Markdown tables, including header, delimiter, and body rows.

Never split an atomic structure merely to satisfy a target chunk size. If an atomic block exceeds the configured chunk size, emit it as one chunk with `oversize_atomic: true`.

Ordinary prose may be split only when necessary for the configured size limit. Splitting must not drop, reorder, or duplicate normalized extracted text.

## Anti-skimming contract

The extractor manifest is the authoritative coverage universe for the Markdown source. Every emitted chunk must receive exactly one entry in `<run-root>/evidence/chunk-evidence.json`: atomic extractive byte-anchored assertions/constraints or an explicit `non_match` with a reason, followed by one `chunk_verified` event.

Finding the requested fact early does not end traversal. If the manifest emits 12 chunks, all 12 must be evidenced and discretely verified before Definition of Done can pass. Generate `<run-root>/deliverables/TRAVERSAL_REPORT.md` from the canonical manifest/evidence pair after traversal.

`text_byte_start` and `text_byte_end` refer to the normalized extracted UTF-8 text stream, not raw file byte offsets. The manifest binds those spans to per-chunk hashes and the full extracted-text hash.

## Command

Read current helper help before first use, then run one bounded extraction operation:

```text
python scripts/extract_markdown.py --help
python scripts/extract_markdown.py INPUT.md --run-root <run-root>
```

The exact CLI shown by `--help` is authoritative if it differs from this example.

The compliant-run manifest is `<run-root>/evidence/chunk-manifest.json`. The low-level `--out` option is reserved for isolated testing and verifier reproduction.
