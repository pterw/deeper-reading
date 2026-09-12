# Deliverable Contract

A substantial document workflow has **three output layers**. Do not confuse them.

All emitted output belongs to one run root. See [Run workspace](run-workspace.md).

## 1. Requested user-facing deliverable

Produce exactly what the user asked for: an answer/analysis, extracted data, transformed file, comparison/audit, or other explicit artifact. Do not replace that result with process logs, a review, a summary, or a derivative format the user did not request.

When the requested result is a generated file, write it under `<run-root>/deliverables/`. Inline conversational answers are returned normally and are recorded in `run.json` as the requested deliverable state; they do not require an invented file solely to satisfy the filesystem contract.

## 2. User-visible traversal proof

Every substantial exhaustive-read run also emits `<run-root>/deliverables/TRAVERSAL_REPORT.md`. This is a lightweight proof ledger, not a prose summary. It is deterministically rendered from the canonical `evidence/chunk-manifest.json` + `evidence/chunk-evidence.json` pair and maps every chunk ID to:

- page/heading/OOXML/HTML locator;
- outcome: `evidence` or `non_match`;
- each atomic extractive assertion/constraint, or the explicit non-match reason.

`TRAVERSAL_REPORT.md` is **grouped by canonical chunk**: it contains a run summary, compact chunk index, and one detail section per chunk. A chunk's human-readable locator and block kinds are shown once, with all byte-anchored atoms nested beneath it. The raw canonical locator remains available for auditability.

For bounded human/agent inspection outside the generated report, use the supported read-only helper `scripts/inspect_chunks.py` with `--summary` or an ordinal range via `--from` / `--to`. This helper reads the canonical manifest; it does not alter coverage or evidence.

`TRAVERSAL_REPORT.md` is part of the standard user-visible completion surface. It must not contain hand-written abstractive summaries that are absent from `chunk-evidence.json`. If the report cannot be reproduced byte-for-byte from the canonical machine evidence, DoD fails.

## 3. Machine/audit evidence bundle

Every substantial run uses this namespace:

```text
<run-root>/
├── plan.md
├── run.json
├── source/
├── evidence/
│   ├── skill-preflight.md
│   ├── source-manifest.md
│   ├── chunk-manifest.json
│   ├── chunk-evidence.json
│   ├── failure-ledger.md
│   ├── verification-log.txt
│   ├── format-qa.md
│   └── ... optional renders/extracts/diffs/preflight ...
├── deliverables/
│   ├── TRAVERSAL_REPORT.md
│   └── ... requested generated files ...
└── dod.json
```

`evidence/chunk-manifest.json`, `evidence/chunk-evidence.json`, `run.json`, and `dod.json` are machine/audit artifacts by default; return them when the user requests machine proof, an audit bundle, or debugging evidence.

## Deliverable identity

`run.json` records:

- `deliverable.requested`: concise description of the requested result;
- `deliverable.provided`: whether that result exists;
- `deliverable.paths`: exact requested-result file paths, when applicable; every path must resolve under `<run-root>/deliverables/`;
- `deliverable.traversal_report`: `deliverables/TRAVERSAL_REPORT.md`;
- `deliverable.notes`: optional clarification, never a substitute for the result.

The exact same traversal-report path must be bound by the `chunking`, `evidence`, and `deliverable` contracts.

## Prohibited substitutions

```text
read paper != write review
extract table != summarize table
verify source != verify derivative
produce requested PDF != produce QA PNGs
answer question != produce process log
TRAVERSAL_REPORT.md != high-level summary
```

If the requested deliverable cannot be produced, DoD is not reached merely because traversal proof is complete. Follow failure recovery and disclose the unresolved deliverable.

A generated file outside `<run-root>/deliverables/` cannot satisfy `deliverable.paths`; scattered output is treated as unverified state, not completion evidence.
