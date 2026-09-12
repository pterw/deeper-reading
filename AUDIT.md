# Deeper-Reading v0.2.0 Hardening Audit

Date: 2026-09-11

## Audit target

Release candidate: `deeper-reading` **0.2.0**.

This release hardens the v0.1.0 exhaustive-traversal contract before any semantic edge/hyperedge layer is introduced. Security and extraction correctness remain below the evidence layer: later evidence, reporting, and future relational features may rely only on source bytes that the package can reproduce and verify.

The v0.1.0 baseline collected **193 tests**. The v0.2.0 candidate collects **261 tests** after adding receipt-containment, extraction-loss, verifier-shape/timeout, evidence-binding, DeepSeek first-run regression, chunk-inspection, grouped-report, and mutation coverage.

## Product invariant

The product is **exhaustive document traversal**, not chunking and not semantic interpretation.

The canonical extractor manifest defines the source chunk universe. Every emitted chunk requires exactly one verified `evidence` or explicit `non_match` verdict plus one ordered `chunk_verified` event before Done is reachable. Fresh final verification re-extracts the original source and requires the reproduced canonical manifest to match.

Extractive evidence proves source contact and byte fidelity. It does **not** prove model comprehension, semantic truth, or correctness of higher-order interpretation.

## v0.2.0 hardening results

### Receipt-owned path containment

`.install-receipt.json` is treated as untrusted input. Receipt-derived paths are rejected before read/hash/remove operations when they are:

- absolute paths;
- parent traversal (`..`);
- Windows drive spellings;
- UNC-like spellings;
- symlink-resolved escapes outside the managed install root.

`force=True` may still bypass modified-managed-file refusal, but it cannot bypass containment.

The release regression suite includes both upgrade and uninstall attack cases and verifies that external victim files remain unchanged.

### HTML text exhaustiveness

The HTML extractor now retains every non-skipped DOM text node exactly once unless that text belongs to an existing atomic table or preformatted block. `script`, `style`, `noscript`, and `template` remain excluded.

Regression coverage includes visible text nested in generic `div`, `section`, `article`, inline-span, list, and body flow so the extractor cannot silently emit an incomplete canonical universe while returning success.

### Heading hierarchy completeness

Structural heading paths now support levels 1 through 6 for:

- Markdown `#` through `######`;
- HTML `h1` through `h6`;
- DOCX `Heading1` through `Heading6`.

Existing H1-H3 behavior remains covered.

### Verifier fail-closed behavior

Malformed run-ledger structures now become deterministic violations instead of uncaught attribute/type errors. Non-object top-level JSON, malformed mapping contracts, and non-object event entries fail diagnostically.

Source re-extraction is bounded by a **60-second timeout**. Timeout becomes a verifier violation rather than an unbounded verifier process.

The historical distinction is preserved:

```text
missing chunking contract -> "chunking contract is required"
present but malformed chunking -> "chunking must be an object"
```

That distinction was recovered after the full pre-freeze suite exposed a regression in the first Task-4 implementation.

## Evidence substrate

### Schema compatibility

Existing evidence schema **v1 remains accepted**.

The supported production evidence builder emits schema **v2**, adding deterministic `atom_id` values derived from:

```text
canonical chunk id
+ atom kind
+ exact chunk byte start/end
+ short SHA-256 of exact text
```

Atom IDs identify byte-verified extractive spans. They are not semantic truth claims.

### Exact quote binding

The generic machinery demonstrated by DeepSeek's first run was promoted into production as `scripts/evidence_atoms.py` and `scripts/build_evidence.py`.

Binding rules are intentionally stricter than the prototype:

- a unique exact quote may bind automatically;
- a missing quote fails with source-derived repair context;
- repeated identical text is ambiguous and requires an explicit byte span;
- explicit spans must reproduce the exact UTF-8 bytes;
- partial/wrong spans fail;
- no partial output is written on binding failure.

The prototype's first-occurrence `bytes.find()` behavior was **not** copied as an identity rule.

## DeepSeek first-run regression corpus

The first real deeper-reading run is preserved as provenance and regression material under `tests/fixtures/deepseek-first-run/`.

Invariant:

```text
70 canonical chunks
70 verdicts
192 assertions
```

The original run-local scripts are preserved byte-for-byte under the fixture's `prototype/` directory but are not imported or executed as trusted production code. The production binder rebinds the supplied first-run corpus and reproduces the known-good text/span semantics while adding v2 atom IDs.

## Human audit surfaces

DeepSeek's useful `dump_chunks.py` behavior was promoted into supported, format-neutral tooling:

- `scripts/chunk_view.py` owns compact human rendering;
- `scripts/inspect_chunks.py` provides bounded manifest inspection;
- `TRAVERSAL_REPORT.md` is grouped by canonical chunk rather than repeating a full locator row for every assertion.

The canonical report now contains:

```text
Run summary
Chunk index
Chunk details
  one locator per chunk
  nested assertions/constraints
  exact byte spans
  atom IDs for schema-v2 evidence
  full raw locator for auditability
```

`chunk-evidence.json` remains machine authority. The verifier deterministically regenerates the report and rejects edited/stale report bytes.

## Source-tree verification evidence

The current tree collects **261 tests**.

A single monolithic `pytest -q` exceeds this chat execution harness's roughly 45-second command window because several verifier tests intentionally perform real extraction/reproduction per case. This is an execution-surface constraint, not an unresolved test failure. The complete collected universe was therefore verified in bounded partitions, following the repository's established release process.

Pre-version-bump accounting on the exact candidate tree:

```text
94  installer + anti-skimming documentation
19  anti-skimming ledger
32  chunk inspection + contradictions + evidence builder + extractors
32  hard-standalone docs/release + native verifier + process skills + payload
30  release evidence + run-root + installer sovereignty + traversal report + workflow
22  mutation suite
32  verify_run suite
---
261/261 GREEN
```

After bumping `VERSION` to `0.2.0`, the immediate release-contract gate passed:

```text
90/90 GREEN
```

covering `tests/test_hard_standalone_release_contract.py`, `tests/test_portable_payload.py`, and the complete installer test tree.

## Mutation evidence

Focused v0.2 security/evidence mutation coverage accounts for **51 tests** across:

```text
tests/test_mutations.py
+ tests/installer/test_install_mutations.py
+ tests/test_evidence_builder.py
```

Those tests cover the new containment, extraction, schema-v2 atom, repeated-quote, malformed-ledger, timeout, and grouped-report boundaries in addition to the existing workflow mutations. Full details live in `MUTATION_REPORT.md`.

## Extracted-archive verification evidence

A release candidate archive was built only through the repository's tested distribution CLI and extracted into a fresh scratch directory.

The extracted archive independently collected **261 tests** and the same complete universe passed in bounded partitions:

```text
94 + 19 + 32 + 32 + 30 + 22 + 32 = 261/261 GREEN
```

Additional extracted-byte targeted smoke:

```text
DeepSeek first-run rebinding: 70 chunks / 192 assertions PASS
malicious receipt containment cases PASS
```

Native packaged-byte pipeline smoke passed for both required formats:

```text
Markdown:
extract -> canonical manifest -> draft evidence -> schema-v2 ledger
-> traversal report -> verify_run PASS

HTML with generic div/section text:
extract -> canonical manifest -> draft evidence -> schema-v2 ledger
-> traversal report -> verify_run PASS
```

The HTML smoke also asserts the generic `div` and `section` phrases survive exactly once in canonical extracted text.

## Freeze rule

`AUDIT.md` and `MUTATION_REPORT.md` are themselves packaged bytes. Therefore the final archive SHA-256 is **not embedded into either file**: doing so would mutate the archive and invalidate the digest being recorded.

The established repository release invariant is instead:

1. finish these audit/mutation records;
2. build the final archive from those bytes;
3. extract and verify the frozen candidate;
4. invoke `verification-before-completion` on the final bytes;
5. compute the final archive SHA-256;
6. emit companion `FINAL_VERIFICATION.md` containing that digest;
7. make **no archive change after hash**.

`FINAL_VERIFICATION.md` is therefore the external hash anchor for the frozen release artifact.

## Historical hard-standalone evidence retained

v0.2.0 extends rather than erases the verified v0.1 hard-standalone release record. The prior pre-freeze checkpoint was **189/189 GREEN** before the final release-evidence tests expanded that release's inventory to the 193-test baseline used by this plan.

The standalone runtime still has **no required Superpowers runtime prerequisite**. Canonical package-owned process skills remain, including:

```text
skills/exhaustive-document-traversal/SKILL.md
skills/verifying-exhaustive-traversal/SKILL.md
```

Bundled extraction capability remains:

```text
scripts/extract_pdf.py
scripts/extract_docx.py
scripts/extract_html.py
scripts/extract_markdown.py
```

Those historical facts are retained because the v0.2 hardening release builds directly on that sovereign standalone contract rather than replacing it.
