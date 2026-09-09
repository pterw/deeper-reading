# Evidence Contract

The evidence bundle proves **exhaustive traversal** and workflow state. It is not a substitute for the requested result.

## Run workspace

All emitted evidence is namespaced beneath one run root. See [Run workspace](run-workspace.md) for the binding path rules.

```text
<run-root>/
  run.json
  plan.md
  source/
  evidence/
    skill-preflight.md
    source-manifest.md
    chunk-manifest.json
    chunk-evidence.json
    failure-ledger.md
    verification-log.txt
    format-qa.md
    renders/
    extracts/
    diffs/
    preflight/
  deliverables/
    TRAVERSAL_REPORT.md
    ... requested generated files ...
  dod.json
```

Keep evidence for different source documents/runs separate. Inputs may live outside the run root; emitted proof may not.

## Authoritative anti-skimming pair

`evidence/chunk-manifest.json` is emitted by a bundled format extractor and defines the complete canonical chunk universe. `evidence/chunk-evidence.json` is the machine evidence ledger. Completion requires a one-to-one mapping from every manifest chunk to exactly one ledger verdict.

Each manifest chunk records a stable `id`/`ordinal`, format-specific locator, normalized-text byte offsets, `content_sha256`, exact emitted content, and source/manifest hashes.

### Atomic extractive evidence

Evidence entries are **not prose summaries**. Every assertion/constraint is an atomic extractive span bound to exact bytes inside its chunk:

```json
{
  "schema_version": 1,
  "manifest_sha256": "...",
  "source_sha256": "...",
  "entries": [
    {
      "chunk_id": "html-000001-...",
      "ordinal": 1,
      "chunk_sha256": "...",
      "outcome": "evidence",
      "assertions": [
        {
          "text": "exact source assertion",
          "chunk_byte_start": 128,
          "chunk_byte_end": 150
        }
      ],
      "constraints": []
    },
    {
      "chunk_id": "html-000002-...",
      "ordinal": 2,
      "chunk_sha256": "...",
      "outcome": "non_match",
      "reason": "No material claim relevant to the requested analysis; chunk still traversed and checked."
    }
  ]
}
```

For `evidence`, every assertion/constraint object must contain non-empty `text` plus `chunk_byte_start`/`chunk_byte_end`; those bytes must reproduce `text` exactly from the canonical chunk. Free-form assertion strings are invalid because they can reintroduce abstractive drift. A `non_match` reason is an explicit traversal verdict, not source extraction.

If extraction emits 12 chunks, the ledger must contain 12 unique valid verdicts. Selected quotations, high-level summaries, or early relevant hits cannot shrink the universe.

## Discrete traversal events

The run event stream must include exactly one `chunk_verified` event per canonical manifest chunk, in manifest order. For 12 emitted chunks there are 12 discrete `chunk_verified` events before final verification. The event stream cannot stop at chunk 4 merely because the answer was found.

## Human-readable traversal proof

`scripts/traversal_report.py --run-root <run-root>` renders `<run-root>/deliverables/TRAVERSAL_REPORT.md` from the canonical manifest/evidence pair. It maps each chunk ID to its locator, verdict, and every atomic extractive assertion/constraint or non-match reason.

`TRAVERSAL_REPORT.md` is deterministic. `scripts/verify_run.py` regenerates the canonical report from the machine evidence and rejects a missing, forged, stale, hand-edited, or noncanonical report.

## `run.json` chunk contract

```json
{
  "chunking": {
    "manifest": "evidence/chunk-manifest.json",
    "manifest_sha256": "...",
    "evidence_ledger": "evidence/chunk-evidence.json",
    "traversal_report": "deliverables/TRAVERSAL_REPORT.md"
  },
  "coverage": {
    "required": ["chunk-id-1", "chunk-id-2"],
    "completed": ["chunk-id-1", "chunk-id-2"]
  },
  "deliverable": {
    "traversal_report": "deliverables/TRAVERSAL_REPORT.md"
  },
  "evidence": {
    "plan_status": "plan.md",
    "skill_preflight": "evidence/skill-preflight.md",
    "source_manifest": "evidence/source-manifest.md",
    "chunk_ledger": "evidence/chunk-evidence.json",
    "failure_ledger": "evidence/failure-ledger.md",
    "verification_log": "evidence/verification-log.txt",
    "format_qa": "evidence/format-qa.md",
    "traversal_report": "deliverables/TRAVERSAL_REPORT.md"
  }
}
```

`coverage` is an **optional** derived mirror only. It never defines or shrinks the coverage universe. Any supplied `required`/`completed` lists must exactly mirror the canonical manifest/evidence order.

## Canonical-universe reproduction

The supplied manifest is not trusted merely because its own hashes are self-consistent. `scripts/verify_run.py` re-runs the bundled extractor against the bound source bytes with the manifest's extraction parameters and requires the reproduced manifest to match exactly. A forged 4-chunk manifest derived from a source that canonically emits 12 chunks therefore fails.

The verifier's reproduction scratch may live in an OS temporary directory because it is ephemeral and automatically cleaned. It cannot satisfy any run evidence predicate; only canonical files inside `<run-root>` count toward DoD.

## Other run evidence

`run.json` also identifies source identity/fidelity, runtime/document profile, skill preflight, written plan, execution events, format QA, and requested deliverable. Evidence paths are resolved relative to `run.json` and must land at the canonical run-root locations.

Core event vocabulary includes `plan_written`, `execution_started`, `node_started`, `chunk_verified`, `node_passed`, `node_failed`, `failure_diagnosed`, `node_rechunked`, `node_recovered`, `node_superseded`, `architecture_stop`, `paths_exhausted`, `disclosure`, `alternative_designed`, `plan_revised`, `verification_started`, `verification_passed`, and `done`.

`evidence/failure-ledger.md` exists even for clean runs (`No failures.` is sufficient). `evidence/verification-log.txt` records fresh final proving actions after the last material change.

## Machine verification

```text
python scripts/verify_run.py <run-root>/run.json
```

The verifier writes `<run-root>/dod.json`. Exit 0 means the machine-checkable traversal predicates passed. It does not waive required visual/structural QA for PDF/DOCX figures, equations, tables, native fields, comments, or layout.
