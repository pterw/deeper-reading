# Traversal Report

## Run summary

- Source: `C:\ssw\dr-live-deepseek2\runs\anti-skimming\source\anti-skimming-plan.md`
- Format: `markdown`
- Source SHA-256: `b4d4182e1c88f8856da49184ed3e29899cec597098d8b0ef6bd4c23416647840`
- Canonical chunks: 14
- Evidence verdicts: 14
- Non-match verdicts: 1
- Assertions: 71
- Constraints: 0

## Chunk index

| # | Chunk | Location | Kinds | Outcome | Atoms |
|---:|---|---|---|---|---:|
| 1 | `markdown-000001-af8cb22b12cb` | `Anti-Skimming Portable Extraction Remediation Plan` | `heading+text` | `evidence` | 7 |
| 2 | `markdown-000002-0935af6dec34` | `Anti-Skimming Portable Extraction Remediation Plan > Global constraints` | `heading+text` | `evidence` | 12 |
| 3 | `markdown-000003-eb0f14e0fb17` | `Anti-Skimming Portable Extraction Remediation Plan > Task 1 — RED portable payload contract` | `heading+text` | `evidence` | 3 |
| 4 | `markdown-000004-0286dad1e76c` | `Anti-Skimming Portable Extraction Remediation Plan > Task 2 — RED chunk-manifest contract` | `heading+text` | `evidence` | 3 |
| 5 | `markdown-000005-bf26ca19205a` | `Anti-Skimming Portable Extraction Remediation Plan > Task 3 — GREEN shared chunk core + Markdown extractor` | `heading+text` | `evidence` | 5 |
| 6 | `markdown-000006-5cb86521229b` | `Anti-Skimming Portable Extraction Remediation Plan > Task 4 — GREEN HTML/DOCX/PDF extractors` | `heading+text` | `evidence` | 4 |
| 7 | `markdown-000007-051a230150ab` | `Anti-Skimming Portable Extraction Remediation Plan > Task 5 — RED anti-skimming verifier` | `heading+text` | `evidence` | 2 |
| 8 | `markdown-000008-6bd529adc97b` | `Anti-Skimming Portable Extraction Remediation Plan > Task 6 — GREEN anti-skimming verifier` | `heading+text` | `evidence` | 6 |
| 9 | `markdown-000009-e023bf8d6abf` | `Anti-Skimming Portable Extraction Remediation Plan > Task 7 — Update references without semantic drift` | `heading+text` | `evidence` | 5 |
| 10 | `markdown-000010-1eb2044d5beb` | `Anti-Skimming Portable Extraction Remediation Plan > Task 8 — Mutation tests` | `heading+text` | `evidence` | 3 |
| 11 | `markdown-000011-6b4f3ccd0089` | `Anti-Skimming Portable Extraction Remediation Plan > Task 9 — Real-source smoke` | `heading+text` | `evidence` | 3 |
| 12 | `markdown-000012-1f46e1271824` | `Anti-Skimming Portable Extraction Remediation Plan > Task 10 — Audit, package, verify` | `heading+text` | `evidence` | 6 |
| 13 | `markdown-000013-c661ccc2bf61` | `Anti-Skimming Portable Extraction Remediation Plan > Definition of Done` | `heading` | `non_match` | 0 |
| 14 | `markdown-000014-d535414423b8` | `Anti-Skimming Portable Extraction Remediation Plan > Definition of Done` | `fenced_code` | `evidence` | 12 |

## Chunk details

### 01 · `markdown-000001-af8cb22b12cb` — Anti-Skimming Portable Extraction Remediation Plan

- Outcome: `evidence`
- Byte span: `0..1092`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan`

**Assertions**

- `markdown-000001-af8cb22b12cb:assertion:80:204:7f80a1bc45af` · bytes `80..204` — REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task. Skill changes follow `superpowers:writing-skills` + TDD.
- `markdown-000001-af8cb22b12cb:assertion:215:402:94b61f8ce6e3` · bytes `215..402` — Make exhaustive, evidenced document traversal the primary enforceable invariant by shipping portable extractors and deriving source-coverage DoD from the extractor-emitted chunk universe.
- `markdown-000001-af8cb22b12cb:assertion:508:633:780e580d1284` · bytes `508..633` — Each extractor emits the complete ordered text-chunk universe with content hashes and contiguous normalized UTF-8 byte spans.
- `markdown-000001-af8cb22b12cb:assertion:634:747:a9bd77f47a47` · bytes `634..747` — A single machine ledger, `chunk-evidence.json`, records exactly one verification verdict for every emitted chunk.
- `markdown-000001-af8cb22b12cb:assertion:748:920:17beb57ab0a5` · bytes `748..920` — `verify_run.py` derives required coverage from the manifest, rejects any missing/extra/duplicate chunk evidence, and refuses Done before the complete manifest is evidenced.
- `markdown-000001-af8cb22b12cb:assertion:921:1028:042c93a0611a` · bytes `921..1028` — Format-specific visual/structural QA remains a separate predicate and is never replaced by text extraction.
- `markdown-000001-af8cb22b12cb:assertion:1054:1091:45c934cfc878` · bytes `1054..1091` — `103 passed` before this remediation.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan"],"kind":"heading","level":1},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan"],"kind":"text"},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan"],"kind":"text"},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan"],"kind":"text"},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan"]}`

</details>

### 02 · `markdown-000002-0935af6dec34` — Anti-Skimming Portable Extraction Remediation Plan > Global constraints

- Outcome: `evidence`
- Byte span: `1092..2315`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Global constraints`

**Assertions**

- `markdown-000002-0935af6dec34:assertion:24:58:79b7a487b164` · bytes `24..58` — Canonical root remains `SKILL.md`.
- `markdown-000002-0935af6dec34:assertion:61:119:3d8b69c4194a` · bytes `61..119` — Freeze remains held until frozen-byte verification passes.
- `markdown-000002-0935af6dec34:assertion:122:192:9280fbefc641` · bytes `122..192` — Portable extraction scripts must not depend on `/home/oai/skills/...`.
- `markdown-000002-0935af6dec34:assertion:195:340:a6dcb8407a61` · bytes `195..340` — Installer remains stdlib-only; extraction helpers may use optional local parsing backends but must fail clearly when no supported backend exists.
- `markdown-000002-0935af6dec34:assertion:343:423:d4344221b49e` · bytes `343..423` — HTML, DOCX, and Markdown extraction must work with Python standard library only.
- `markdown-000002-0935af6dec34:assertion:426:514:49665c7a6a46` · bytes `426..514` — PDF extraction supports environment-detected backends; no internal OAI path is required.
- `markdown-000002-0935af6dec34:assertion:517:631:31ca6fa1b3b5` · bytes `517..631` — Every emitted chunk gets stable id, ordinal, locator, content hash, normalized extracted-text byte span, and text.
- `markdown-000002-0935af6dec34:assertion:634:730:96a052749a9a` · bytes `634..730` — Chunk spans must cover the emitted normalized text stream contiguously with no gaps or overlaps.
- `markdown-000002-0935af6dec34:assertion:733:844:b232aab401f4` · bytes `733..844` — Atomic Markdown fences/tables are never split; oversize atomic blocks remain one chunk and are marked oversize.
- `markdown-000002-0935af6dec34:assertion:847:965:71c44cfb8cc8` · bytes `847..965` — One machine evidence record per chunk: `facts`, `constraints`, or explicit `non_match`; empty/ambiguous verdicts fail.
- `markdown-000002-0935af6dec34:assertion:968:1098:8bdc8967d0f9` · bytes `968..1098` — `coverage.required` and `coverage.completed` may exist for reporting but must exactly mirror manifest/evidence, never define them.
- `markdown-000002-0935af6dec34:assertion:1101:1222:e9a43e21b30c` · bytes `1101..1222` — PDF/DOCX visual/layout truth remains governed by format QA; exhaustive text traversal does not claim visual completeness.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Global constraints"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Global constraints"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Global constraints"]}`

</details>

### 03 · `markdown-000003-eb0f14e0fb17` — Anti-Skimming Portable Extraction Remediation Plan > Task 1 — RED portable payload contract

- Outcome: `evidence`
- Byte span: `2315..2676`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 1 — RED portable payload contract`

**Assertions**

- `markdown-000003-eb0f14e0fb17:assertion:46:204:df7bc60f339b` · bytes `46..204` — Add tests requiring `extract_pdf.py`, `extract_docx.py`, `extract_html.py`, `extract_markdown.py`, shared chunking code, and `references/lengthy-markdown.md`.
- `markdown-000003-eb0f14e0fb17:assertion:207:292:38b0b00ec2ac` · bytes `207..292` — Require `MANIFEST.json` runtime payload to include the complete `scripts/` directory.
- `markdown-000003-eb0f14e0fb17:assertion:295:360:555c6e812d05` · bytes `295..360` — Run targeted tests and observe failure before production changes.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 1 — RED portable payload contract"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 1 — RED portable payload contract"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 1 — RED portable payload contract"]}`

</details>

### 04 · `markdown-000004-0286dad1e76c` — Anti-Skimming Portable Extraction Remediation Plan > Task 2 — RED chunk-manifest contract

- Outcome: `evidence`
- Byte span: `2676..2925`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 2 — RED chunk-manifest contract`

**Assertions**

- `markdown-000004-0286dad1e76c:assertion:44:147:f520deaf3291` · bytes `44..147` — Test schema/version/source identity/chunk ids/ordinals/content hashes/contiguous normalized byte spans.
- `markdown-000004-0286dad1e76c:assertion:150:189:acc96d3124fc` · bytes `150..189` — Test deterministic repeated extraction.
- `markdown-000004-0286dad1e76c:assertion:192:248:62351df337d2` · bytes `192..248` — Test empty document behavior and oversize atomic blocks.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 2 — RED chunk-manifest contract"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 2 — RED chunk-manifest contract"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 2 — RED chunk-manifest contract"]}`

</details>

### 05 · `markdown-000005-bf26ca19205a` — Anti-Skimming Portable Extraction Remediation Plan > Task 3 — GREEN shared chunk core + Markdown extractor

- Outcome: `evidence`
- Byte span: `2925..3267`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 3 — GREEN shared chunk core + Markdown extractor`

**Assertions**

- `markdown-000005-bf26ca19205a:assertion:61:163:2eb2aee5da5c` · bytes `61..163` — Implement block/section parser recognizing `#`, `##`, `###`, fenced code, tables, and ordinary blocks.
- `markdown-000005-bf26ca19205a:assertion:166:201:d0e167215cab` · bytes `166..201` — Keep fenced code and tables atomic.
- `markdown-000005-bf26ca19205a:assertion:204:268:40861eee884d` · bytes `204..268` — Chunk sections to bounded bytes without splitting atomic blocks.
- `markdown-000005-bf26ca19205a:assertion:271:300:f53a3b9649e8` · bytes `271..300` — Emit canonical JSON manifest.
- `markdown-000005-bf26ca19205a:assertion:303:341:b994ef8cc34e` · bytes `303..341` — Run Markdown extractor tests to GREEN.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 3 — GREEN shared chunk core + Markdown extractor"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 3 — GREEN shared chunk core + Markdown extractor"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 3 — GREEN shared chunk core + Markdown extractor"]}`

</details>

### 06 · `markdown-000006-5cb86521229b` — Anti-Skimming Portable Extraction Remediation Plan > Task 4 — GREEN HTML/DOCX/PDF extractors

- Outcome: `evidence`
- Byte span: `3267..3706`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 4 — GREEN HTML/DOCX/PDF extractors`

**Assertions**

- `markdown-000006-5cb86521229b:assertion:47:140:ff867eaec274` · bytes `47..140` — HTML: stdlib DOM parser, heading-aware blocks, preserve pre/code/table text as atomic blocks.
- `markdown-000006-5cb86521229b:assertion:143:270:654c1769a81c` · bytes `143..270` — DOCX: stdlib ZIP/XML extraction across document/header/footer/footnotes/endnotes/comments story parts with structural locators.
- `markdown-000006-5cb86521229b:assertion:273:381:09690bb0c155` · bytes `273..381` — PDF: backend auto-detection (`pypdf`, PyMuPDF, pdfplumber, or `pdftotext`) with page locators; no OAI paths.
- `markdown-000006-5cb86521229b:assertion:384:438:31cb7fe2a0fa` · bytes `384..438` — Run each extractor test independently before widening.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 4 — GREEN HTML/DOCX/PDF extractors"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 4 — GREEN HTML/DOCX/PDF extractors"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 4 — GREEN HTML/DOCX/PDF extractors"]}`

</details>

### 07 · `markdown-000007-051a230150ab` — Anti-Skimming Portable Extraction Remediation Plan > Task 5 — RED anti-skimming verifier

- Outcome: `evidence`
- Byte span: `3706..4109`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 5 — RED anti-skimming verifier`

**Assertions**

- `markdown-000007-051a230150ab:assertion:43:117:64c40e24e7ed` · bytes `43..117` — Extend run schema with `chunking.manifest` and `chunking.evidence_ledger`.
- `markdown-000007-051a230150ab:assertion:120:402:2e50d3b535df` · bytes `120..402` — RED cases: missing evidence for chunk N, forged smaller `coverage.required`, duplicate chunk evidence, evidence for nonexistent chunk, skipped ordinal, content-hash mismatch, manifest source mismatch, premature Done after partial traversal, empty verdict, and stale completion list.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 5 — RED anti-skimming verifier"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 5 — RED anti-skimming verifier"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 5 — RED anti-skimming verifier"]}`

</details>

### 08 · `markdown-000008-6bd529adc97b` — Anti-Skimming Portable Extraction Remediation Plan > Task 6 — GREEN anti-skimming verifier

- Outcome: `evidence`
- Byte span: `4109..4613`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 6 — GREEN anti-skimming verifier`

**Assertions**

- `markdown-000008-6bd529adc97b:assertion:45:101:d269165b78f1` · bytes `45..101` — Load manifest and evidence fresh relative to `run.json`.
- `markdown-000008-6bd529adc97b:assertion:104:161:296bacf17848` · bytes `104..161` — Validate manifest internal integrity and source identity.
- `markdown-000008-6bd529adc97b:assertion:164:285:b537708107d7` · bytes `164..285` — Require exact set equality: manifest chunk ids == evidence chunk ids == coverage.required == coverage.completed for Done.
- `markdown-000008-6bd529adc97b:assertion:288:371:f634bc7a3022` · bytes `288..371` — Require one and only one evidence record per chunk with nonempty supported verdict.
- `markdown-000008-6bd529adc97b:assertion:374:431:14bdc4569190` · bytes `374..431` — Make `source_coverage_complete` derive from these checks.
- `markdown-000008-6bd529adc97b:assertion:434:503:7c6f3a47c758` · bytes `434..503` — Produce per-chunk violations that identify the missing/invalid chunk.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 6 — GREEN anti-skimming verifier"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 6 — GREEN anti-skimming verifier"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 6 — GREEN anti-skimming verifier"]}`

</details>

### 09 · `markdown-000009-e023bf8d6abf` — Anti-Skimming Portable Extraction Remediation Plan > Task 7 — Update references without semantic drift

- Outcome: `evidence`
- Byte span: `4613..5160`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 7 — Update references without semantic drift`

**Assertions**

- `markdown-000009-e023bf8d6abf:assertion:57:94:4b07b3c26e83` · bytes `57..94` — Add `references/lengthy-markdown.md`.
- `markdown-000009-e023bf8d6abf:assertion:97:215:679d023c119f` · bytes `97..215` — Update root `SKILL.md`, DoD, evidence, deliverable, control-flow, HTML/PDF/DOCX/runtime-profile/dependency references.
- `markdown-000009-e023bf8d6abf:assertion:218:342:9ecac13dc1af` · bytes `218..342` — State primary mission explicitly: exhaustive verified traversal; chunking is the enforcement mechanism, not the deliverable.
- `markdown-000009-e023bf8d6abf:assertion:345:441:3b16aacd293a` · bytes `345..441` — Preserve native render-first PDF/DOCX visual QA and distinguish it from portable text traversal.
- `markdown-000009-e023bf8d6abf:assertion:444:546:58632db7a118` · bytes `444..546` — Remove/replace stale language that allows selected-chunk summaries or needle-in-a-haystack early exit.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 7 — Update references without semantic drift"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 7 — Update references without semantic drift"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 7 — Update references without semantic drift"]}`

</details>

### 10 · `markdown-000010-1eb2044d5beb` — Anti-Skimming Portable Extraction Remediation Plan > Task 8 — Mutation tests

- Outcome: `evidence`
- Byte span: `5160..5510`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 8 — Mutation tests`

**Assertions**

- `markdown-000010-1eb2044d5beb:assertion:31:70:712fd5e6f6ed` · bytes `31..70` — Begin from a passing full-manifest run.
- `markdown-000010-1eb2044d5beb:assertion:73:279:8b7e74bab3f2` · bytes `73..279` — Mutate: delete one ledger entry; truncate manifest; forge coverage; reorder/duplicate ids; replace fact/non-match with empty record; Done after first N chunks; change chunk content hash; change source hash.
- `markdown-000010-1eb2044d5beb:assertion:282:349:35bdff7bd47a` · bytes `282..349` — Every illegal mutation must be rejected for the intended predicate.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 8 — Mutation tests"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 8 — Mutation tests"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 8 — Mutation tests"]}`

</details>

### 11 · `markdown-000011-6b4f3ccd0089` — Anti-Skimming Portable Extraction Remediation Plan > Task 9 — Real-source smoke

- Outcome: `evidence`
- Byte span: `5510..5819`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 9 — Real-source smoke`

**Assertions**

- `markdown-000011-6b4f3ccd0089:assertion:34:162:251f61366bac` · bytes `34..162` — Exercise at least one real public HTML or PDF through extractor -> manifest -> complete evidence ledger -> `verify_run.py` PASS.
- `markdown-000011-6b4f3ccd0089:assertion:165:227:75d65544ecde` · bytes `165..227` — Mutate one emitted chunk to missing evidence -> verifier FAIL.
- `markdown-000011-6b4f3ccd0089:assertion:230:308:ba61786afbae` · bytes `230..308` — Record exact scope; do not claim visual PDF completeness from text extraction.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 9 — Real-source smoke"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 9 — Real-source smoke"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 9 — Real-source smoke"]}`

</details>

### 12 · `markdown-000012-1f46e1271824` — Anti-Skimming Portable Extraction Remediation Plan > Task 10 — Audit, package, verify

- Outcome: `evidence`
- Byte span: `5819..6173`
- Kinds: `heading+text`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Task 10 — Audit, package, verify`

**Assertions**

- `markdown-000012-1f46e1271824:assertion:40:96:70a8d89bb8bd` · bytes `40..96` — Re-read changed Markdown and scripts for contradictions.
- `markdown-000012-1f46e1271824:assertion:99:119:d466bbc8e863` · bytes `99..119` — Run full test suite.
- `markdown-000012-1f46e1271824:assertion:122:162:af44246c9df1` · bytes `122..162` — Build distribution using tested builder.
- `markdown-000012-1f46e1271824:assertion:165:224:cc724a995b4c` · bytes `165..224` — Extract frozen ZIP and rerun full suite from archive bytes.
- `markdown-000012-1f46e1271824:assertion:227:283:debbac5050b7` · bytes `227..283` — Run real-source anti-skimming smoke from archived bytes.
- `markdown-000012-1f46e1271824:assertion:286:353:a21efaa91b93` · bytes `286..353` — Invoke `verification-before-completion`, hash archive, then freeze.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 10 — Audit, package, verify"],"kind":"heading","level":2},{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 10 — Audit, package, verify"],"kind":"text"}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Task 10 — Audit, package, verify"]}`

</details>

### 13 · `markdown-000013-c661ccc2bf61` — Anti-Skimming Portable Extraction Remediation Plan > Definition of Done

- Outcome: `non_match`
- Byte span: `6173..6195`
- Kinds: `heading`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Definition of Done`

**Non-match reason**

Heading only ('## Definition of Done'); the Definition of Done body is emitted as chunk 14, which carries the acceptance predicates.

<details><summary>Full locator</summary>

`{"blocks":[{"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Definition of Done"],"kind":"heading","level":2}],"heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Definition of Done"]}`

</details>

### 14 · `markdown-000014-d535414423b8` — Anti-Skimming Portable Extraction Remediation Plan > Definition of Done

- Outcome: `evidence`
- Byte span: `6195..6695`
- Kinds: `fenced_code`
- Locator: `Anti-Skimming Portable Extraction Remediation Plan > Definition of Done`

**Assertions**

- `markdown-000014-d535414423b8:assertion:8:35:a89c3e5f8725` · bytes `8..35` — portable_extractors_shipped
- `markdown-000014-d535414423b8:assertion:40:72:341d08307e18` · bytes `40..72` — extractor_manifest_deterministic
- `markdown-000014-d535414423b8:assertion:77:138:4e7ae568be86` · bytes `77..138` — every_manifest_chunk_has_exactly_one_verified_evidence_record
- `markdown-000014-d535414423b8:assertion:143:195:717c8542f4e1` · bytes `143..195` — no_manifest_chunk_can_be_omitted_by_forging_coverage
- `markdown-000014-d535414423b8:assertion:200:226:1e79c848e3fc` · bytes `200..226` — premature_done_is_rejected
- `markdown-000014-d535414423b8:assertion:231:268:312562f469cf` · bytes `231..268` — markdown_fences_and_tables_are_atomic
- `markdown-000014-d535414423b8:assertion:273:309:873acf5227a0` · bytes `273..309` — native_visual_qa_semantics_preserved
- `markdown-000014-d535414423b8:assertion:314:350:2d440e84b535` · bytes `314..350` — portable_payload_contains_extractors
- `markdown-000014-d535414423b8:assertion:355:375:bf4051db98dd` · bytes `355..375` — mutation_suite_green
- `markdown-000014-d535414423b8:assertion:380:418:3afc8e589eec` · bytes `380..418` — real_source_full_traversal_smoke_green
- `markdown-000014-d535414423b8:assertion:423:462:521167c289ca` · bytes `423..462` — existing_installer_workflow_tests_green
- `markdown-000014-d535414423b8:assertion:467:495:b49198e23d6c` · bytes `467..495` — frozen_archive_retests_green

<details><summary>Full locator</summary>

`{"atomic_kind":"fenced_code","heading_path":["Anti-Skimming Portable Extraction Remediation Plan","Definition of Done"],"kind":"fenced_code"}`

</details>
