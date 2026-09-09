# Contributing to deeper-reading

Thank you for helping improve **`deeper-reading`**!

`deeper-reading` enforces exhaustive document traversal and anti-skimming verification for autonomous agents reading dense, complex documents.

---

## Core Principles & Invariants

1. **Exhaustive Traversal is the Mission; Chunking is the Ruler**:
   - The canonical extractor manifest defines the chunk universe.
   - Every single emitted chunk must receive exactly one atomic extractive `evidence` verdict (with exact byte offsets) or an explicit `non_match` reason.
   - Finding an early match or useful fact is never authorization to stop traversal.

2. **Tamper-Proof Verification**:
   - `scripts/verify_run.py` re-extracts the original source bytes independently using the bundled extractor.
   - Forged or hand-edited manifests cannot shrink the required coverage universe.

3. **Standard-Library Only for Core Extractors**:
   - Bundled extractors (`extract_html.py`, `extract_docx.py`, `extract_markdown.py`, `extract_pdf.py`) must operate with zero mandatory third-party package dependencies.
   - PDF extraction uses runtime backend detection (`pypdf`, `pymupdf`, `pdfplumber`, `pdftotext`).

4. **Package-Owned Process Skills**:
   - Orchestration is self-contained in `skills/` (`exhaustive-document-traversal`, `planning-document-traversal`, `executing-document-traversal`, `debugging-document-workflows`, `recovering-document-workflows`, `verifying-exhaustive-traversal`).

---

## Testing & Quality Gate

Before submitting any pull request or committing changes:

### 1. Run the Full Test Suite
```bash
python -m pytest
```
All 192+ tests (unit tests, mutation tests, anti-skimming ledger tests, and installer transaction tests) must pass.

### 2. Verify the Installer
```bash
python installer/install.py doctor --target generic-agents --json
```
Ensure all bundled extractors report `ready` and the standalone document profile resolves cleanly.

---

## Adding New Extractors or Formats

If contributing support for an additional document format:
1. Implement the extractor in `scripts/extract_<format>.py` adhering to the `Block`, `pack_blocks`, and `build_manifest` schema from `scripts/chunk_common.py`.
2. Ensure it supports both `--out <path>` and `--run-root <path>`.
3. Add deterministic test coverage in `tests/test_extractors.py`.
4. Document the format's structural invariants in a dedicated `references/<format>.md`.
