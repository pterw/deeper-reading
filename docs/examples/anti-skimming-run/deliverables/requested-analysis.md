# What must be true for this plan to count as finished?

Source: `source/anti-skimming-plan.md` (sha256 `b4d4182e1c88f8856da49184ed3e29899cec597098d8b0ef6bd4c23416647840`, 6814 bytes, 14 canonical chunks).
Every quotation below is an exact byte span from the chunk named beside it. Chunk ids are the canonical manifest ids.

## 1. The terminal acceptance set

The plan's own closing block is the authoritative finish condition. It is a conjunction: every line must hold.

Chunk `markdown-000014-d535414423b8` (the fenced `text` block under `## Definition of Done`):

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

Each of those twelve names is an acceptance check in its own right:

| # | Acceptance check (exact quote) | Chunk |
|---|---|---|
| 1 | `portable_extractors_shipped` | `markdown-000014-d535414423b8` |
| 2 | `extractor_manifest_deterministic` | `markdown-000014-d535414423b8` |
| 3 | `every_manifest_chunk_has_exactly_one_verified_evidence_record` | `markdown-000014-d535414423b8` |
| 4 | `no_manifest_chunk_can_be_omitted_by_forging_coverage` | `markdown-000014-d535414423b8` |
| 5 | `premature_done_is_rejected` | `markdown-000014-d535414423b8` |
| 6 | `markdown_fences_and_tables_are_atomic` | `markdown-000014-d535414423b8` |
| 7 | `native_visual_qa_semantics_preserved` | `markdown-000014-d535414423b8` |
| 8 | `portable_payload_contains_extractors` | `markdown-000014-d535414423b8` |
| 9 | `mutation_suite_green` | `markdown-000014-d535414423b8` |
| 10 | `real_source_full_traversal_smoke_green` | `markdown-000014-d535414423b8` |
| 11 | `existing_installer_workflow_tests_green` | `markdown-000014-d535414423b8` |
| 12 | `frozen_archive_retests_green` | `markdown-000014-d535414423b8` |

The heading chunk `markdown-000013-c661ccc2bf61` contains only `## Definition of Done`; the predicates themselves are in chunk 14.

## 2. Goal, architecture and baseline rules

Chunk `markdown-000001-af8cb22b12cb`:

- "REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task. Skill changes follow `superpowers:writing-skills` + TDD." — a process rule: the plan is executed task-by-task, and skill changes are TDD.
- "Make exhaustive, evidenced document traversal the primary enforceable invariant by shipping portable extractors and deriving source-coverage DoD from the extractor-emitted chunk universe." — the goal: coverage DoD is derived from the extractor's chunk universe, not from a hand-written list.
- "Each extractor emits the complete ordered text-chunk universe with content hashes and contiguous normalized UTF-8 byte spans." — every extractor must emit the complete ordered universe, with hashes and contiguous spans.
- "A single machine ledger, `chunk-evidence.json`, records exactly one verification verdict for every emitted chunk." — one ledger, one verdict per chunk.
- "`verify_run.py` derives required coverage from the manifest, rejects any missing/extra/duplicate chunk evidence, and refuses Done before the complete manifest is evidenced." — the verifier derives coverage from the manifest and refuses Done early.
- "Format-specific visual/structural QA remains a separate predicate and is never replaced by text extraction." — visual/structural QA is a separate predicate and cannot be substituted by text extraction.
- "`103 passed` before this remediation." — the regression baseline is 103 passing tests before the work starts.

## 3. Global constraints (chunk `markdown-000002-0935af6dec34`)

Every bullet is a constraint that must still hold at the end:

1. "Canonical root remains `SKILL.md`."
2. "Freeze remains held until frozen-byte verification passes."
3. "Portable extraction scripts must not depend on `/home/oai/skills/...`."
4. "Installer remains stdlib-only; extraction helpers may use optional local parsing backends but must fail clearly when no supported backend exists."
5. "HTML, DOCX, and Markdown extraction must work with Python standard library only."
6. "PDF extraction supports environment-detected backends; no internal OAI path is required."
7. "Every emitted chunk gets stable id, ordinal, locator, content hash, normalized extracted-text byte span, and text."
8. "Chunk spans must cover the emitted normalized text stream contiguously with no gaps or overlaps."
9. "Atomic Markdown fences/tables are never split; oversize atomic blocks remain one chunk and are marked oversize."
10. "One machine evidence record per chunk: `facts`, `constraints`, or explicit `non_match`; empty/ambiguous verdicts fail."
11. "`coverage.required` and `coverage.completed` may exist for reporting but must exactly mirror manifest/evidence, never define them."
12. "PDF/DOCX visual/layout truth remains governed by format QA; exhaustive text traversal does not claim visual completeness."

## 4. Per-task acceptance checks

### Task 1 — RED portable payload contract (chunk `markdown-000003-eb0f14e0fb17`)

- "Add tests requiring `extract_pdf.py`, `extract_docx.py`, `extract_html.py`, `extract_markdown.py`, shared chunking code, and `references/lengthy-markdown.md`."
- "Require `MANIFEST.json` runtime payload to include the complete `scripts/` directory."
- "Run targeted tests and observe failure before production changes." — the RED gate: failure must be observed before production code changes.

### Task 2 — RED chunk-manifest contract (chunk `markdown-000004-0286dad1e76c`)

- "Test schema/version/source identity/chunk ids/ordinals/content hashes/contiguous normalized byte spans."
- "Test deterministic repeated extraction."
- "Test empty document behavior and oversize atomic blocks."

### Task 3 — GREEN shared chunk core + Markdown extractor (chunk `markdown-000005-bf26ca19205a`)

- "Implement block/section parser recognizing `#`, `##`, `###`, fenced code, tables, and ordinary blocks."
- "Keep fenced code and tables atomic."
- "Chunk sections to bounded bytes without splitting atomic blocks."
- "Emit canonical JSON manifest."
- "Run Markdown extractor tests to GREEN."

### Task 4 — GREEN HTML/DOCX/PDF extractors (chunk `markdown-000006-5cb86521229b`)

- "HTML: stdlib DOM parser, heading-aware blocks, preserve pre/code/table text as atomic blocks."
- "DOCX: stdlib ZIP/XML extraction across document/header/footer/footnotes/endnotes/comments story parts with structural locators."
- "PDF: backend auto-detection (`pypdf`, PyMuPDF, pdfplumber, or `pdftotext`) with page locators; no OAI paths."
- "Run each extractor test independently before widening."

### Task 5 — RED anti-skimming verifier (chunk `markdown-000007-051a230150ab`)

- "Extend run schema with `chunking.manifest` and `chunking.evidence_ledger`."
- "RED cases: missing evidence for chunk N, forged smaller `coverage.required`, duplicate chunk evidence, evidence for nonexistent chunk, skipped ordinal, content-hash mismatch, manifest source mismatch, premature Done after partial traversal, empty verdict, and stale completion list." — ten named rejection cases.

### Task 6 — GREEN anti-skimming verifier (chunk `markdown-000008-6bd529adc97b`)

- "Load manifest and evidence fresh relative to `run.json`."
- "Validate manifest internal integrity and source identity."
- "Require exact set equality: manifest chunk ids == evidence chunk ids == coverage.required == coverage.completed for Done."
- "Require one and only one evidence record per chunk with nonempty supported verdict."
- "Make `source_coverage_complete` derive from these checks."
- "Produce per-chunk violations that identify the missing/invalid chunk."

### Task 7 — Update references without semantic drift (chunk `markdown-000009-e023bf8d6abf`)

- "Add `references/lengthy-markdown.md`."
- "Update root `SKILL.md`, DoD, evidence, deliverable, control-flow, HTML/PDF/DOCX/runtime-profile/dependency references."
- "State primary mission explicitly: exhaustive verified traversal; chunking is the enforcement mechanism, not the deliverable."
- "Preserve native render-first PDF/DOCX visual QA and distinguish it from portable text traversal."
- "Remove/replace stale language that allows selected-chunk summaries or needle-in-a-haystack early exit."

### Task 8 — Mutation tests (chunk `markdown-000010-1eb2044d5beb`)

- "Begin from a passing full-manifest run."
- "Mutate: delete one ledger entry; truncate manifest; forge coverage; reorder/duplicate ids; replace fact/non-match with empty record; Done after first N chunks; change chunk content hash; change source hash." — eight named mutations.
- "Every illegal mutation must be rejected for the intended predicate." — rejection must be for the intended predicate, not any failure.

### Task 9 — Real-source smoke (chunk `markdown-000011-6b4f3ccd0089`)

- "Exercise at least one real public HTML or PDF through extractor -> manifest -> complete evidence ledger -> `verify_run.py` PASS."
- "Mutate one emitted chunk to missing evidence -> verifier FAIL."
- "Record exact scope; do not claim visual PDF completeness from text extraction."

### Task 10 — Audit, package, verify (chunk `markdown-000012-1f46e1271824`)

- "Re-read changed Markdown and scripts for contradictions."
- "Run full test suite."
- "Build distribution using tested builder."
- "Extract frozen ZIP and rerun full suite from archive bytes."
- "Run real-source anti-skimming smoke from archived bytes."
- "Invoke `verification-before-completion`, hash archive, then freeze." — the closing sequence: verify, hash, freeze.

## 5. Statements made late that change or narrow earlier ones

Each entry names the earlier statement and the later statement. "Earlier" means the lower-numbered chunk; "later" means the higher-numbered chunk. Quotes are exact.

1. **Byte spans vs atomic blocks.**
   Earlier (chunk `markdown-000001-af8cb22b12cb`): "Each extractor emits the complete ordered text-chunk universe with content hashes and contiguous normalized UTF-8 byte spans."
   Later (chunk `markdown-000002-0935af6dec34`): "Atomic Markdown fences/tables are never split; oversize atomic blocks remain one chunk and are marked oversize."
   The later rule narrows the span rule: an oversize fence or table stays one chunk and is marked oversize instead of being split to fit.

2. **Contiguity vs bounded bytes.**
   Earlier (chunk `markdown-000002-0935af6dec34`): "Chunk spans must cover the emitted normalized text stream contiguously with no gaps or overlaps."
   Later (chunk `markdown-000005-bf26ca19205a`): "Chunk sections to bounded bytes without splitting atomic blocks."
   The later rule makes atomic blocks an explicit exception to the byte bound.

3. **Reporting lists become a Done condition.**
   Earlier (chunk `markdown-000002-0935af6dec34`): "`coverage.required` and `coverage.completed` may exist for reporting but must exactly mirror manifest/evidence, never define them."
   Later (chunk `markdown-000008-6bd529adc97b`): "Require exact set equality: manifest chunk ids == evidence chunk ids == coverage.required == coverage.completed for Done."
   Optional reporting lists become mandatory: all four sets must be equal, not merely consistent.

4. **Derivation becomes a freshness rule.**
   Earlier (chunk `markdown-000001-af8cb22b12cb`): "`verify_run.py` derives required coverage from the manifest, rejects any missing/extra/duplicate chunk evidence, and refuses Done before the complete manifest is evidenced."
   Later (chunk `markdown-000008-6bd529adc97b`): "Load manifest and evidence fresh relative to `run.json`."
   The later rule narrows "derives" to a freshness requirement: a cached or stale read does not count.

5. **Verdict vocabulary becomes "nonempty supported verdict".**
   Earlier (chunk `markdown-000002-0935af6dec34`): "One machine evidence record per chunk: `facts`, `constraints`, or explicit `non_match`; empty/ambiguous verdicts fail."
   Later (chunk `markdown-000008-6bd529adc97b`): "Require one and only one evidence record per chunk with nonempty supported verdict."
   The later rule narrows the three-way vocabulary to "nonempty supported verdict" and makes uniqueness explicit.

6. **Separation becomes render-first ordering.**
   Earlier (chunk `markdown-000001-af8cb22b12cb`): "Format-specific visual/structural QA remains a separate predicate and is never replaced by text extraction."
   Later (chunk `markdown-000009-e023bf8d6abf`): "Preserve native render-first PDF/DOCX visual QA and distinguish it from portable text traversal."
   The later rule fixes the order (render-first) and requires the two QA kinds to be distinguished, not merely kept separate.

7. **Backend set is narrowed and page locators are added.**
   Earlier (chunk `markdown-000002-0935af6dec34`): "PDF extraction supports environment-detected backends; no internal OAI path is required."
   Later (chunk `markdown-000006-5cb86521229b`): "PDF: backend auto-detection (`pypdf`, PyMuPDF, pdfplumber, or `pdftotext`) with page locators; no OAI paths."
   The later rule names exactly four backends, adds page locators, and widens "no internal OAI path" to "no OAI paths".

8. **One forbidden prefix becomes any OAI path.**
   Earlier (chunk `markdown-000002-0935af6dec34`): "Portable extraction scripts must not depend on `/home/oai/skills/...`."
   Later (chunk `markdown-000006-5cb86521229b`): "PDF: backend auto-detection (`pypdf`, PyMuPDF, pdfplumber, or `pdftotext`) with page locators; no OAI paths."
   The later rule widens the prohibition from one path prefix to any OAI path.

9. **Frozen-byte verification becomes a concrete procedure.**
   Earlier (chunk `markdown-000002-0935af6dec34`): "Freeze remains held until frozen-byte verification passes."
   Later (chunk `markdown-000012-1f46e1271824`): "Extract frozen ZIP and rerun full suite from archive bytes."
   The later rule narrows the freeze gate to extracting the frozen ZIP and rerunning the full suite from the archive bytes.

10. **The freeze gate becomes an ordered sequence.**
    Earlier (chunk `markdown-000002-0935af6dec34`): "Freeze remains held until frozen-byte verification passes."
    Later (chunk `markdown-000012-1f46e1271824`): "Invoke `verification-before-completion`, hash archive, then freeze."
    The later rule fixes the order: verify, hash the archive, then freeze.

11. **TDD becomes an observable RED gate.**
    Earlier (chunk `markdown-000001-af8cb22b12cb`): "REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task. Skill changes follow `superpowers:writing-skills` + TDD."
    Later (chunk `markdown-000003-eb0f14e0fb17`): "Run targeted tests and observe failure before production changes."
    The later rule narrows "TDD" to a visible failure before any production change.

12. **A second required sub-skill is added at the end.**
    Earlier (chunk `markdown-000001-af8cb22b12cb`): "REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task."
    Later (chunk `markdown-000012-1f46e1271824`): "Invoke `verification-before-completion`, hash archive, then freeze."
    The plan is not finished on `executing-plans` alone; a second sub-skill is required before the freeze.

13. **The terminal predicate names a narrower test set than Task 10.**
    Earlier (chunk `markdown-000012-1f46e1271824`): "Run full test suite."
    Later (chunk `markdown-000014-d535414423b8`): "existing_installer_workflow_tests_green"
    The DoD line names only the existing installer workflow tests. The full suite remains a Task 10 step; the DoD line alone does not carry it.

14. **The 103-test baseline is not a terminal predicate.**
    Earlier (chunk `markdown-000001-af8cb22b12cb`): "`103 passed` before this remediation."
    Later (chunk `markdown-000014-d535414423b8`): "existing_installer_workflow_tests_green"
    The baseline is a starting measurement, not the finish line; the DoD names installer workflow tests only.

15. **The separation rule becomes a named predicate.**
    Earlier (chunk `markdown-000001-af8cb22b12cb`): "Format-specific visual/structural QA remains a separate predicate and is never replaced by text extraction."
    Later (chunk `markdown-000014-d535414423b8`): "native_visual_qa_semantics_preserved"
    The general rule becomes a terminal predicate that must be shown true.

16. **The no-claim rule is narrowed to the smoke test.**
    Earlier (chunk `markdown-000002-0935af6dec34`): "PDF/DOCX visual/layout truth remains governed by format QA; exhaustive text traversal does not claim visual completeness."
    Later (chunk `markdown-000011-6b4f3ccd0089`): "Record exact scope; do not claim visual PDF completeness from text extraction."
    The later rule requires the smoke to record its exact scope and forbids a visual-completeness claim from text extraction.

17. **The chunk field list becomes a test list.**
    Earlier (chunk `markdown-000002-0935af6dec34`): "Every emitted chunk gets stable id, ordinal, locator, content hash, normalized extracted-text byte span, and text."
    Later (chunk `markdown-000004-0286dad1e76c`): "Test schema/version/source identity/chunk ids/ordinals/content hashes/contiguous normalized byte spans."
    The later rule narrows the fields to those the tests must assert and adds schema, version and source identity as tested properties.

18. **The empty-verdict rule becomes a named mutation.**
    Earlier (chunk `markdown-000002-0935af6dec34`): "One machine evidence record per chunk: `facts`, `constraints`, or explicit `non_match`; empty/ambiguous verdicts fail."
    Later (chunk `markdown-000010-1eb2044d5beb`): "Mutate: delete one ledger entry; truncate manifest; forge coverage; reorder/duplicate ids; replace fact/non-match with empty record; Done after first N chunks; change chunk content hash; change source hash."
    The later rule turns the empty-verdict rule into a specific mutation that must be rejected.

19. **Two edge cases are added to the span rule.**
    Earlier (chunk `markdown-000002-0935af6dec34`): "Chunk spans must cover the emitted normalized text stream contiguously with no gaps or overlaps."
    Later (chunk `markdown-000004-0286dad1e76c`): "Test empty document behavior and oversize atomic blocks."
    The later rule adds the empty document and the oversize atomic block as cases the span rule must survive.

20. **Optional backends are narrowed to four.**
    Earlier (chunk `markdown-000002-0935af6dec34`): "Installer remains stdlib-only; extraction helpers may use optional local parsing backends but must fail clearly when no supported backend exists."
    Later (chunk `markdown-000006-5cb86521229b`): "PDF: backend auto-detection (`pypdf`, PyMuPDF, pdfplumber, or `pdftotext`) with page locators; no OAI paths."
    The later rule names the four backends and ties the clear-failure requirement to auto-detection finding none of them.

21. **The ledger's location becomes a schema obligation.**
    Earlier (chunk `markdown-000001-af8cb22b12cb`): "A single machine ledger, `chunk-evidence.json`, records exactly one verification verdict for every emitted chunk."
    Later (chunk `markdown-000007-051a230150ab`): "Extend run schema with `chunking.manifest` and `chunking.evidence_ledger`."
    The later rule requires the run to name both the manifest and the evidence ledger, not just to have one ledger.

22. **The goal becomes required prose.**
    Earlier (chunk `markdown-000001-af8cb22b12cb`): "Make exhaustive, evidenced document traversal the primary enforceable invariant by shipping portable extractors and deriving source-coverage DoD from the extractor-emitted chunk universe."
    Later (chunk `markdown-000009-e023bf8d6abf`): "State primary mission explicitly: exhaustive verified traversal; chunking is the enforcement mechanism, not the deliverable."
    The later rule narrows the goal into required wording: the mission must be stated explicitly, and chunking must be described as the mechanism, not the deliverable.

23. **Completeness gains determinism.**
    Earlier (chunk `markdown-000001-af8cb22b12cb`): "Each extractor emits the complete ordered text-chunk universe with content hashes and contiguous normalized UTF-8 byte spans."
    Later (chunk `markdown-000004-0286dad1e76c`): "Test deterministic repeated extraction."
    The later rule adds that repeated extraction must produce the same result.

24. **The separation rule extends to prose cleanup.**
    Earlier (chunk `markdown-000001-af8cb22b12cb`): "Format-specific visual/structural QA remains a separate predicate and is never replaced by text extraction."
    Later (chunk `markdown-000009-e023bf8d6abf`): "Remove/replace stale language that allows selected-chunk summaries or needle-in-a-haystack early exit."
    The later rule extends the separation rule to the documentation: stale language permitting early exit must be removed or replaced.

## 6. What the document does not state

These are honest gaps, not requirements:

- No numeric coverage threshold is given beyond "every emitted chunk"; the universe is whatever the extractor emits.
- No test count is required at the end. `103 passed` is only the pre-remediation baseline.
- "Supported verdict" is not defined beyond the earlier `facts`, `constraints`, or explicit `non_match` vocabulary.
- No named distribution builder, ZIP name, or hash algorithm is given; Task 10 says only `Build distribution using tested builder` and `hash archive`.
- No owner, date, or review gate is named for the freeze beyond `verification-before-completion`.
