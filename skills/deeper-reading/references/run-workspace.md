# Run Workspace Contract

The **run root is the output proof boundary** for one document workflow execution. Every artifact emitted by the workflow belongs to that run root. Original user-provided inputs may remain outside it.

## Canonical layout

```text
<run-root>/
├── run.json
├── plan.md
├── source/
│   └── ...                    # only local source copies/downloads created by this run
├── evidence/
│   ├── chunk-manifest.json
│   ├── chunk-evidence.json
│   ├── source-manifest.md
│   ├── skill-preflight.md
│   ├── failure-ledger.md
│   ├── format-qa.md
│   ├── verification-log.txt
│   ├── renders/
│   ├── extracts/
│   ├── diffs/
│   └── preflight/
├── deliverables/
│   ├── TRAVERSAL_REPORT.md
│   └── ...                    # requested generated files, when any
└── dod.json
```

Only create optional subdirectories when needed.

## Path rules

- `run.json`, `plan.md`, and `dod.json` live directly at `<run-root>`.
- The extractor manifest is always `<run-root>/evidence/chunk-manifest.json`.
- The atomic machine ledger is always `<run-root>/evidence/chunk-evidence.json`.
- QA/debug/proving artifacts live under `<run-root>/evidence/`.
- `TRAVERSAL_REPORT.md` and all requested generated files live under `<run-root>/deliverables/`.
- If the workflow downloads, converts, or deliberately copies a source for this run, place that emitted local source under `<run-root>/source/`.
- A user-provided original source does **not** need to be copied into the run root merely to satisfy this layout; it is an input, not an emitted artifact.
- Temporary reproduction files created internally by `scripts/verify_run.py` may use an OS temporary directory because they are ephemeral verifier scratch, not completion evidence. They must be cleaned automatically and cannot satisfy any DoD predicate.

## Extractor interface

For a compliant run, use the run-root interface (note: when running in an external workspace, resolve `scripts/` relative to the installed skill root, e.g. `<skill-root>/scripts/...`):

```text
python <skill-root>/scripts/extract_html.py SOURCE --run-root <run-root>
python <skill-root>/scripts/extract_markdown.py SOURCE --run-root <run-root>
python <skill-root>/scripts/extract_docx.py SOURCE --run-root <run-root>
python <skill-root>/scripts/extract_pdf.py SOURCE --run-root <run-root>
```

The low-level `--out PATH` extractor option exists for isolated testing and verifier re-extraction. A final run must bind its canonical manifest at `evidence/chunk-manifest.json`.

Render the human proof with:

```text
python scripts/traversal_report.py --run-root <run-root>
```

Verify with:

```text
python scripts/verify_run.py <run-root>/run.json
```

The verifier writes `<run-root>/dod.json` itself. Supplying `--write-dod` is allowed only when it resolves to that same canonical path.

## Completion rule

A file outside the run root cannot satisfy an emitted-artifact predicate. A requested generated deliverable outside `<run-root>/deliverables/`, a machine evidence file outside `<run-root>/evidence/`, or a noncanonical manifest/report path makes the run **NOT DONE**.

This rule exists for auditability: one directory must contain everything needed to inspect what the workflow emitted, what it proved, and what it returned to the user.
