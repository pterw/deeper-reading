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
   - `skills/deeper-reading/scripts/verify_run.py` re-extracts the original source bytes independently using the bundled extractor.
   - Forged or hand-edited manifests cannot shrink the required coverage universe.

3. **Explicit Runtime Dependencies**:
   - HTML, DOCX and Markdown extractors use the Python standard library.
   - PDF extraction requires a detected backend (`pypdf`, `pymupdf`, `pdfplumber`, `pdftotext`); adapters must record its version and actual capabilities.
   - Backend installation is opt-in. CI installs `requirements-optional.txt` to exercise PDF fixtures.

4. **Package-Owned Process Skills**:
   - Orchestration is self-contained in `skills/deeper-reading/modules/` as `<name>.md` files (`exhaustive-document-traversal`, `planning-document-traversal`, `executing-document-traversal`, `debugging-document-workflows`, `recovering-document-workflows`, `verifying-exhaustive-traversal`).

---

## Testing & Quality Gate

Before submitting any pull request or committing changes, run the commands in
the `gates` block under
[AGENTS.md "Gates"](https://github.com/pterw/deeper-reading/blob/main/AGENTS.md#gates),
as [AGENTS.md "Done means"](https://github.com/pterw/deeper-reading/blob/main/AGENTS.md#done-means)
requires. That file owns the commands, so they are not copied here. Install the
tools first with `python -m pip install pytest ruff==0.16.10 -r requirements-optional.txt`
(CI runs `python -m ruff check .`, so lint before you push).
CI also runs `agentskills validate skills/deeper-reading`; the pin is in `.github/workflows/ci.yml`.

---

## Adding New Extractors or Formats

If contributing support for an additional document format:
1. Implement the extractor in `skills/deeper-reading/scripts/extract_<format>.py` adhering to the `Block`, `pack_blocks`, and `build_manifest` schema from `skills/deeper-reading/scripts/chunk_common.py`.
2. Ensure it supports both `--out <path>` and `--run-root <path>`.
3. Register it in `EXTRACTOR_SCRIPTS` in `skills/deeper-reading/scripts/verify_run.py`, so the verifier can re-extract the source.
4. Document the format's structural invariants in a reference under `skills/deeper-reading/references/`, named for the format (`skills/deeper-reading/references/html.md`, `skills/deeper-reading/references/pdf.md`, `skills/deeper-reading/references/lengthy-markdown.md`).
5. Add the format's route to `skills/deeper-reading/modules/exhaustive-document-traversal.md`, linking that reference.
6. Add deterministic test coverage in `tests/test_extractors.py`, and update `tests/test_phase_gated_loading.py` for the new route and reference.
7. Record images, SVG and diagrams through `MediaCollector` in `skills/deeper-reading/scripts/chunk_common.py`, and add a row to `tests/test_media_extractors.py`.

Other changes have a matching list of files to update: see the
[AGENTS.md "Maintenance Matrix"](https://github.com/pterw/deeper-reading/blob/main/AGENTS.md#maintenance-matrix).
