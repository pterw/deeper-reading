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

### Evidence construction and schema compatibility

**Schema v1 remains accepted** for existing ledgers. Schema v1 atoms are identified by their exact text plus `chunk_byte_start` / `chunk_byte_end` span.

The supported production builder, `scripts/build_evidence.py`, accepts draft verdicts and emits **schema v2**. Schema v2 preserves the same extractive byte contract and adds a deterministic `atom_id` derived from canonical chunk ID, atom kind, exact byte span, and a short SHA-256 of the exact text. `atom_id` is an address for later references; it is not evidence of semantic truth or model comprehension.

Draft atoms may provide exact quoted text alone when that quote occurs exactly once in the canonical chunk. If the same quote occurs more than once, the binding is **ambiguous** and the draft must provide an **explicit byte span** selecting the intended occurrence. The builder validates that an explicit span reproduces the quoted UTF-8 bytes exactly. A missing quote, wrong span, duplicate/missing chunk verdict, or empty `non_match` reason fails without writing a partial ledger.

```text
python scripts/build_evidence.py evidence/chunk-manifest.json draft-evidence.json \
  --out evidence/chunk-evidence.json
```

The builder fills canonical chunk IDs and hashes from the manifest rather than trusting draft copies. `chunk-evidence.json` remains the coverage authority paired with `chunk-manifest.json`; schema v2 does not create a separate semantic authority.

## Discrete traversal events

The run event stream must include exactly one `chunk_verified` event per canonical manifest chunk, in manifest order. For 12 emitted chunks there are 12 discrete `chunk_verified` events before final verification. The event stream cannot stop at chunk 4 merely because the answer was found.

## Human-readable traversal proof

`scripts/traversal_report.py --run-root <run-root>` renders `<run-root>/deliverables/TRAVERSAL_REPORT.md` from the canonical manifest/evidence pair. The report is grouped by canonical chunk: a compact run summary and chunk index lead to one detail section per chunk, with its locator rendered once and all atomic assertions/constraints or the non-match reason nested beneath it.

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

The supplied manifest is not trusted merely because its own hashes are self-consistent. `scripts/verify_run.py` re-runs the bundled extractor against the bound source bytes with the manifest's extraction parameters and requires the reproduced manifest to match exactly, except that the absolute `source.path` is not compared (`source.sha256` and `size_bytes` still bind the bytes, and the run folder may have moved). A relative `source.local_path` in `run.json` resolves against the run folder. A forged 4-chunk manifest derived from a source that canonically emits 12 chunks therefore fails.

The verifier's reproduction scratch may live in an OS temporary directory because it is ephemeral and automatically cleaned. It cannot satisfy any run evidence predicate; only canonical files inside `<run-root>` count toward DoD.

## Other run evidence

`run.json` also identifies source identity/fidelity, runtime/document profile, skill preflight, written plan, execution events, format QA, and requested deliverable. Evidence paths are resolved relative to `run.json` and must land at the canonical run-root locations.

### Skill preflight receipts

`evidence/skill-preflight.md` records each selected-path reference before its
gate is crossed. Write it as a Markdown table with the columns `Reference path`,
`Required gate`, and `Completed`, one row per selected-path reference:

| Reference path | Required gate | Completed |
| --- | --- | --- |
| references/evidence.md | before the evidence ledger is built | yes |

The agent must not set the final `required_references_read` aggregate to true
while a selected-path row is missing, incomplete, or recorded after its gate.
The verifier checks only that the aggregate is true and that the file exists; it
does not read the rows. The table is human-audited evidence; it adds no machine
schema or event type. See [Definition of done](definition-of-done.md) for which
proofs are only existence-checked.

Core event vocabulary includes `plan_written`, `execution_started`, `node_started`, `chunk_verified`, `node_passed`, `node_failed`, `failure_diagnosed`, `node_rechunked`, `node_recovered`, `node_superseded`, `architecture_stop`, `paths_exhausted`, `disclosure`, `alternative_designed`, `plan_revised`, `verification_started`, `verification_passed`, and `done`.

`evidence/failure-ledger.md` exists even for clean runs (`No failures.` is sufficient). `evidence/verification-log.txt` records fresh final proving actions after the last material change.

## Machine verification

```text
python scripts/verify_run.py <run-root>/run.json
```

The verifier writes `<run-root>/dod.json`. Exit 0 means the machine-checkable traversal predicates passed. It does not waive required visual/structural QA for PDF/DOCX figures, equations, tables, native fields, comments, or layout.

In `dod.json`, `predicates.deliverable_provided` is a derived alias that always equals `predicates.requested_deliverable_produced`.

## Worked first run

One complete run over a one-chunk source. A test extracts the labelled blocks below verbatim and drives them through the real scripts to `passed: true`, so they cannot drift from the verifier. Run the commands from the skill root (so `scripts/...` resolves) and use `python` or `py`, whichever your runtime has.

The source, saved as `<run-root>/source/source.md`:

```markdown source.md
# Pump notes

The pump must be primed. Do not start a dry pump. The pump must be primed again after service.
```

Placeholders: `<run-root>` is the run folder, `<source>` is `<run-root>/source/source.md`, and `<source-uri>` is the value of `source.uri` in `run.json`. Extract, bind the draft verdicts, then render the report:

```sh first-run
python scripts/extract_markdown.py <source> --run-root <run-root> --source-uri <source-uri>
python scripts/build_evidence.py <run-root>/evidence/chunk-manifest.json <run-root>/draft-evidence.json --out <run-root>/evidence/chunk-evidence.json
python scripts/traversal_report.py --run-root <run-root>
```

The draft verdicts, saved as `<run-root>/draft-evidence.json` before `build_evidence.py` runs. Verdicts are keyed by `ordinal`. The quote `The pump must be primed` occurs twice in the chunk, so the draft gives an explicit span; the offsets count UTF-8 bytes in the chunk `content` of the manifest (extraction normalises whitespace, so they are not source-file offsets):

```json draft-evidence.json
{
  "entries": [
    {
      "ordinal": 1,
      "outcome": "evidence",
      "assertions": [
        {
          "text": "The pump must be primed",
          "chunk_byte_start": 13,
          "chunk_byte_end": 36
        }
      ],
      "constraints": []
    }
  ]
}
```

A chunk with nothing relevant gets `{"ordinal": 2, "outcome": "non_match", "reason": "No claim relevant to the request; chunk traversed."}` instead.

Two hashes go into `run.json`. Compute each with this command, run once for the source file and once for `<run-root>/evidence/chunk-manifest.json` (`<file>` is that path; `sha256sum` is not used because PowerShell lacks it):

```sh sha256
python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <file>
```

Fill the placeholders in `run.json`: `<SOURCE_PATH>` is the source path relative to the run folder (`source/source.md`); `<SOURCE_SHA256>` and `<MANIFEST_SHA256>` come from the `sha256` command; `<CHUNK_ID>` and `<CHUNK_SHA256>` are `chunks[0].id` and `chunks[0].content_sha256` of the manifest. For a run with more chunks, repeat the `chunk_verified` and `node_started` / `node_passed` event triple and one `plan.nodes` entry for every chunk, in manifest order. This is the final state after `done` is appended; the `qa.required` names are the format checks your run owes (see [Definition of done](definition-of-done.md)).

```json run.json
{
  "source": {
    "uri": "https://example.org/pump-notes",
    "local_path": "<SOURCE_PATH>",
    "sha256": "<SOURCE_SHA256>",
    "format": "markdown",
    "authority": "primary",
    "identity_verified": true
  },
  "fidelity": {"preserved": true, "substitutions": []},
  "preflight": {
    "skill_read": true,
    "required_references_read": true,
    "helper_help_read": true,
    "runtime_profile_resolved": true,
    "traversal_plan_ready": true
  },
  "plan": {"path": "plan.md", "nodes": ["acquire", "<CHUNK_ID>"]},
  "events": [
    {"type": "plan_written"},
    {"type": "execution_started"},
    {"type": "node_started", "node": "acquire"},
    {"type": "node_passed", "node": "acquire", "evidence": "evidence/source-manifest.md"},
    {"type": "node_started", "node": "<CHUNK_ID>"},
    {"type": "chunk_verified", "chunk_id": "<CHUNK_ID>", "chunk_sha256": "<CHUNK_SHA256>", "evidence": "evidence/chunk-evidence.json"},
    {"type": "node_passed", "node": "<CHUNK_ID>", "evidence": "evidence/chunk-evidence.json"},
    {"type": "verification_started"},
    {"type": "verification_passed", "evidence": "evidence/verification-log.txt"},
    {"type": "done"}
  ],
  "chunking": {
    "manifest": "evidence/chunk-manifest.json",
    "manifest_sha256": "<MANIFEST_SHA256>",
    "evidence_ledger": "evidence/chunk-evidence.json",
    "traversal_report": "deliverables/TRAVERSAL_REPORT.md"
  },
  "qa": {"required": ["markdown-structure"], "passed": ["markdown-structure"]},
  "deliverable": {
    "requested": "answer",
    "provided": true,
    "paths": [],
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

All eight files named in `evidence` must exist. `build_evidence.py` creates `evidence/chunk-evidence.json` and `traversal_report.py` creates `deliverables/TRAVERSAL_REPORT.md`; the agent writes the other six (`plan.md`, `evidence/skill-preflight.md`, `evidence/source-manifest.md`, `evidence/failure-ledger.md`, `evidence/verification-log.txt`, `evidence/format-qa.md`). The verifier checks that several of them exist, not what they say; see [Definition of done](definition-of-done.md).

Run the verifier last. It may run before `done` is appended (it then enforces node resolution), and it is re-run after `done` is appended:

```sh verify
python scripts/verify_run.py <run-root>/run.json
```

Exit 0 and `"passed": true` in `<run-root>/dod.json` mean the machine-checkable predicates hold. A run that stops short of the last chunk fails here; that is the only failing shape this section shows.
