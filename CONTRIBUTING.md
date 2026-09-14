# Contributing to deeper-reading

Thank you for helping improve **`deeper-reading`**!

`deeper-reading` enforces exhaustive document traversal and anti-skimming verification for autonomous agents reading dense, complex documents.

---

## Core Principles & Invariants

1. **Exhaustive Traversal is the Mission; Chunking is the Ruler**:
   - The canonical extractor manifest defines the chunk universe.
   - Every single emitted chunk must receive exactly one atomic extractive `evidence` verdict (with exact byte offsets) or an explicit `non_match` reason.
   - Finding an early match or useful fact is never authorization to stop traversal.

2. **Source-Bound Verification**:
   - `scripts/verify_run.py` re-extracts the original source bytes independently using the bundled extractor.
   - Forged or hand-edited manifests cannot shrink the required coverage universe.

3. **Explicit Runtime Dependencies**:
   - HTML, DOCX and Markdown extractors use the Python standard library.
   - PDF extraction requires a detected backend (`pypdf`, `pymupdf`, `pdfplumber`, `pdftotext`); adapters must record its version and actual capabilities.
   - Backend installation is opt-in. CI installs `requirements-optional.txt` to exercise PDF fixtures.

4. **Package-Owned Process Skills**:
   - Orchestration is self-contained in `skills/` (`exhaustive-document-traversal`, `planning-document-traversal`, `executing-document-traversal`, `debugging-document-workflows`, `recovering-document-workflows`, `verifying-exhaustive-traversal`).

---

## Testing & Quality Gate

Before submitting any pull request or committing changes:

### 1. Run the Full Test Suite
```bash
python -m pytest
```
All tests must pass. Installer changes also require `npm test` and
`npm run test:pack-smoke`. Cross-runtime transaction tests need Node.js;
CI enforces the named skip budgets in `tests/check_skip_budget.py`.

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
