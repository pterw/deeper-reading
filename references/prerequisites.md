# Standalone Runtime Preflight

The normal runtime is package-owned. External process frameworks are not required for planning, execution, debugging, recovery, or verification.

This package-owned state machine is the **user-approved orchestration** for this skill and is **already-brainstormed**. Do not reopen design work at normal startup; reserve redesign for a genuinely **novel design** requirement or the explicit architecture-stop recovery path.

## Required preflight

Before document processing, establish and record:

```json
{
  "skill_read": true,
  "required_references_read": true,
  "helper_help_read": true,
  "runtime_profile_resolved": true,
  "traversal_plan_ready": true
}
```

- `skill_read`: root `SKILL.md` was read in full.
- `required_references_read`: every reference required by the selected
  source/format path was read in full before its authoritative gate. The final
  value is the compatibility aggregate over the phase receipts below.
- `helper_help_read`: bundled extractor/verifier help needed for the run was read before first use.
- `runtime_profile_resolved`: `standalone` or `oai-native` is explicit.
- `traversal_plan_ready`: the package-owned planning phase produced the written traversal plan before substantial execution.

## Phase receipts

`evidence/skill-preflight.md` records each selected-path reference before its
gate is crossed:

| Reference path | Required gate | Completed |
|---|---|---|
| `references/prerequisites.md` | Activation and contract establishment | yes |

Add one row for every reference selected by the actual source, format, failure,
and verification path. A missing or late row keeps
`required_references_read` false. The table is human-auditable evidence; it
does not add a machine schema or event type.

## Package-owned process sequence

```text
exhaustive-document-traversal
  -> planning-document-traversal
  -> executing-document-traversal
  -> debugging-document-workflows on failure
  -> recovering-document-workflows only after architecture stop / exhausted paths
  -> verifying-exhaustive-traversal
```

Read the corresponding `skills/<name>/SKILL.md` in full before using that phase.

## Failure ordering

A failed node must emit `failure_diagnosed` before repair, re-chunking, sibling traversal, fallback traversal, or downstream work.

After `architecture_stop`, execution cannot continue through another repair branch. The only valid redesign path is:

```text
architecture_stop
  -> paths_exhausted
  -> disclosure
  -> alternative_designed
  -> plan_revised
  -> execution resumes
```

## Optional native enhancement

`oai-native` may add host-native PDF/DOCX rendering, OCR, forms, or visual/layout QA. Those capabilities are optional enhancement layers. They do not own or alter the canonical extraction/chunk/evidence/Done contract.

## Non-repository runs

Ordinary document work is a `document-run`; repository-only lifecycle steps are `not_applicable`. It does not require Git, a worktree, a branch, commits, or repository lifecycle ceremony. **Do not create a Git repository** solely to process a document.
