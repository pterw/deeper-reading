# Traversal Plan: anti-skimming-plan.md

## Task

Answer, from `source/anti-skimming-plan.md` only: "What must be true for this plan to
count as finished?" List every acceptance check, rule and constraint with its exact
quote and source chunk; identify statements made late that change or narrow earlier
statements, naming which is earlier and which is later. Write the answer to
`deliverables/requested-analysis.md`.

## Decomposition

Task -> Batch -> Chunk -> Operation. One operation per shell call.

## Nodes

| Node | Input | Output | Success evidence | Failure boundary | Depends on | Changes source authority/fidelity/semantics? |
|---|---|---|---|---|---|---|
| acquire | `source/anti-skimming-plan.md` | bound source identity | `evidence/source-manifest.md` with path, sha256, size, format, authority | file missing or unreadable | none | no |
| extract | bound source bytes | canonical manifest, 14 chunks | `evidence/chunk-manifest.json` written by `extract_markdown.py --run-root` | extractor non-zero exit | acquire | no |
| chunk-01 .. chunk-14 | manifest chunk N | one verdict for chunk N | entry in `draft-evidence.json`, then `evidence/chunk-evidence.json` | quote not found or ambiguous in chunk | extract | no |
| deliverable | all 14 verdicts | `deliverables/requested-analysis.md` | file exists under run root, answers the question | missing quote or missing late/early pair | chunk-01..14 | no |
| report | manifest + ledger | `deliverables/TRAVERSAL_REPORT.md` | `traversal_report.py --run-root` exit 0 | renderer non-zero exit | deliverable | no |
| verify | run.json + all evidence | `dod.json` | `verify_run.py` exit 0, `"passed": true` | verifier non-zero exit -> debugging-document-workflows | report | no |

## Coverage rule

The manifest is the coverage universe: 14 chunks, each with exactly one `evidence` or
`non_match` verdict, in ordinal order, each with a `chunk_verified` event. No chunk is
skipped because the answer looks complete early.

## Failure boundaries

- A quote that does not occur exactly once in its chunk is a failed node: diagnose,
  then re-bind with an explicit byte span or a different exact quote.
- A verifier failure is diagnosed before any repair; the failure is recorded in
  `evidence/failure-ledger.md`.

## Deliverable contract

`deliverable.requested`: analysis of the plan's completion criteria with exact quotes,
chunk ids, and earlier/later narrowing pairs.
`deliverable.paths`: `deliverables/requested-analysis.md`.
