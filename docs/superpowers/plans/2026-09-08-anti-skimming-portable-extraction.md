# Anti-Skimming Portable Extraction Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task. Skill changes follow `superpowers:writing-skills` + TDD.

**Goal:** Make exhaustive, evidenced document traversal the primary enforceable invariant by shipping portable extractors and deriving source-coverage DoD from the extractor-emitted chunk universe.

**Architecture:** `scripts/` owns environment-agnostic extraction and a canonical chunk-manifest schema. Each extractor emits the complete ordered text-chunk universe with content hashes and contiguous normalized UTF-8 byte spans. A single machine ledger, `chunk-evidence.json`, records exactly one verification verdict for every emitted chunk. `verify_run.py` derives required coverage from the manifest, rejects any missing/extra/duplicate chunk evidence, and refuses Done before the complete manifest is evidenced. Format-specific visual/structural QA remains a separate predicate and is never replaced by text extraction.

**Regression baseline:** `103 passed` before this remediation.

## Global constraints

- Canonical root remains `SKILL.md`.
- Freeze remains held until frozen-byte verification passes.
- Portable extraction scripts must not depend on `/home/oai/skills/...`.
- Installer remains stdlib-only; extraction helpers may use optional local parsing backends but must fail clearly when no supported backend exists.
- HTML, DOCX, and Markdown extraction must work with Python standard library only.
- PDF extraction supports environment-detected backends; no internal OAI path is required.
- Every emitted chunk gets stable id, ordinal, locator, content hash, normalized extracted-text byte span, and text.
- Chunk spans must cover the emitted normalized text stream contiguously with no gaps or overlaps.
- Atomic Markdown fences/tables are never split; oversize atomic blocks remain one chunk and are marked oversize.
- One machine evidence record per chunk: `facts`, `constraints`, or explicit `non_match`; empty/ambiguous verdicts fail.
- `coverage.required` and `coverage.completed` may exist for reporting but must exactly mirror manifest/evidence, never define them.
- PDF/DOCX visual/layout truth remains governed by format QA; exhaustive text traversal does not claim visual completeness.

## Task 1 — RED portable payload contract
- Add tests requiring `extract_pdf.py`, `extract_docx.py`, `extract_html.py`, `extract_markdown.py`, shared chunking code, and `references/lengthy-markdown.md`.
- Require `MANIFEST.json` runtime payload to include the complete `scripts/` directory.
- Run targeted tests and observe failure before production changes.

## Task 2 — RED chunk-manifest contract
- Test schema/version/source identity/chunk ids/ordinals/content hashes/contiguous normalized byte spans.
- Test deterministic repeated extraction.
- Test empty document behavior and oversize atomic blocks.

## Task 3 — GREEN shared chunk core + Markdown extractor
- Implement block/section parser recognizing `#`, `##`, `###`, fenced code, tables, and ordinary blocks.
- Keep fenced code and tables atomic.
- Chunk sections to bounded bytes without splitting atomic blocks.
- Emit canonical JSON manifest.
- Run Markdown extractor tests to GREEN.

## Task 4 — GREEN HTML/DOCX/PDF extractors
- HTML: stdlib DOM parser, heading-aware blocks, preserve pre/code/table text as atomic blocks.
- DOCX: stdlib ZIP/XML extraction across document/header/footer/footnotes/endnotes/comments story parts with structural locators.
- PDF: backend auto-detection (`pypdf`, PyMuPDF, pdfplumber, or `pdftotext`) with page locators; no OAI paths.
- Run each extractor test independently before widening.

## Task 5 — RED anti-skimming verifier
- Extend run schema with `chunking.manifest` and `chunking.evidence_ledger`.
- RED cases: missing evidence for chunk N, forged smaller `coverage.required`, duplicate chunk evidence, evidence for nonexistent chunk, skipped ordinal, content-hash mismatch, manifest source mismatch, premature Done after partial traversal, empty verdict, and stale completion list.

## Task 6 — GREEN anti-skimming verifier
- Load manifest and evidence fresh relative to `run.json`.
- Validate manifest internal integrity and source identity.
- Require exact set equality: manifest chunk ids == evidence chunk ids == coverage.required == coverage.completed for Done.
- Require one and only one evidence record per chunk with nonempty supported verdict.
- Make `source_coverage_complete` derive from these checks.
- Produce per-chunk violations that identify the missing/invalid chunk.

## Task 7 — Update references without semantic drift
- Add `references/lengthy-markdown.md`.
- Update root `SKILL.md`, DoD, evidence, deliverable, control-flow, HTML/PDF/DOCX/runtime-profile/dependency references.
- State primary mission explicitly: exhaustive verified traversal; chunking is the enforcement mechanism, not the deliverable.
- Preserve native render-first PDF/DOCX visual QA and distinguish it from portable text traversal.
- Remove/replace stale language that allows selected-chunk summaries or needle-in-a-haystack early exit.

## Task 8 — Mutation tests
- Begin from a passing full-manifest run.
- Mutate: delete one ledger entry; truncate manifest; forge coverage; reorder/duplicate ids; replace fact/non-match with empty record; Done after first N chunks; change chunk content hash; change source hash.
- Every illegal mutation must be rejected for the intended predicate.

## Task 9 — Real-source smoke
- Exercise at least one real public HTML or PDF through extractor -> manifest -> complete evidence ledger -> `verify_run.py` PASS.
- Mutate one emitted chunk to missing evidence -> verifier FAIL.
- Record exact scope; do not claim visual PDF completeness from text extraction.

## Task 10 — Audit, package, verify
- Re-read changed Markdown and scripts for contradictions.
- Run full test suite.
- Build distribution using tested builder.
- Extract frozen ZIP and rerun full suite from archive bytes.
- Run real-source anti-skimming smoke from archived bytes.
- Invoke `verification-before-completion`, hash archive, then freeze.

## Definition of Done

```text
portable_extractors_shipped
AND extractor_manifest_deterministic
AND every_manifest_chunk_has_exactly_one_verified_evidence_record
AND no_manifest_chunk_can_be_omitted_by_forging_coverage
AND premature_done_is_rejected
AND markdown_fences_and_tables_are_atomic
AND native_visual_qa_semantics_preserved
AND portable_payload_contains_extractors
AND mutation_suite_green
AND real_source_full_traversal_smoke_green
AND existing_installer_workflow_tests_green
AND frozen_archive_retests_green
```
