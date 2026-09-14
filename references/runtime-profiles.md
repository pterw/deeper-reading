# Runtime and Document Profiles

The package is **standalone by default**. Host-native capabilities may enhance format QA, but they never own or alter the anti-skimming traversal contract.

## standalone

Canonical/default profile.

Owned by this package:

- bundled PDF/DOCX/HTML/Markdown extraction;
- deterministic canonical chunk manifests;
- exhaustive-document-traversal;
- planning-document-traversal;
- executing-document-traversal;
- debugging-document-workflows;
- recovering-document-workflows;
- verifying-exhaustive-traversal;
- atomic extractive `chunk-evidence.json` assertions with byte spans;
- exactly one ordered `chunk_verified` event per canonical emitted chunk;
- deterministic `TRAVERSAL_REPORT.md`;
- source re-extraction and machine DoD verification.

No external process framework is required for normal runtime orchestration.

## PDF provenance

For a PDF run, copy the extractor manifest's `extraction` object into `run.json`:

```json
{"extraction": {"backend": "pypdf 5.3.0", "format": "pdf", "capabilities": ["text"]}}
```

Use the actual backend and version emitted locally, not the example value.
The verifier requires this object, compares it with the independently reproduced
manifest, rejects unknown backends or overstated capabilities, and includes the
record in `dod.json`. Text backends cannot justify an `ocr-verified` QA claim.
Richer QA still needs separately recorded evidence from an approved provider;
it is not inferred from a text library's possible capabilities.

PDF manifests made before 0.2.3 must be regenerated along with their evidence:
chunks now respect page boundaries, including empty pages, and record backend
versions. Changing a backend/version can change text extraction and requires
fresh evidence. Extraction accepts `--password` for encrypted files, but final
verification currently has no password input; it fails closed rather than
storing credentials in a ledger. Use an explicitly approved decrypted source
with its own identity and fidelity record if final verification is required.

The standalone extractors guarantee basic text traversal only. When a task depends on visual layout, equations, figures, scanned text, forms, comments, tracked changes, or other structure they cannot establish, the run must either use an approved enhancement profile/provider or fail closed before claiming that capability was verified.

## oai-native

**Optional enhancement** inside an OpenAI/ChatGPT environment where native document tooling exists.

May add:

- richer PDF rendering and visual comparison;
- OCR;
- PDF form/layout QA;
- DOCX rendering/layout/native-structure checks;
- native helper scripts and format-specific diagnostics.

Invariant:

> `oai-native` may enhance capability, but may NEVER alter the canonical anti-skimming evidence contract.

The package-owned extractors/evidence ledger remain the traversal ground truth unless a future version explicitly migrates that contract under tests. Native helpers cannot shrink the canonical chunk universe, replace atomic evidence with summaries, waive `chunk_verified` coverage, or bypass source re-extraction.

## Resolution rule

Before execution record:

```text
runtime_profile = standalone | oai-native
```

Choose `oai-native` only when its native tools actually exist and the requested task benefits from them. Otherwise use `standalone`.

If required format capability is unavailable, fail closed rather than silently degrading fidelity.
