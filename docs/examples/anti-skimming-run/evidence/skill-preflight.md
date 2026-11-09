# Skill Preflight

Runtime profile: `standalone` (the package-owned default; no `oai-native` capability was
needed or used).

| Reference path | Required gate | Completed |
|---|---|---|
| `references/prerequisites.md` | Activation and contract establishment | yes |
| `references/runtime-profiles.md` | Activation and contract establishment | yes |
| `references/control-flow.md` | Activation and contract establishment | yes |
| `references/deliverable.md` | Before writing the traversal plan | yes |
| `references/definition-of-done.md` | Before writing the traversal plan | yes |
| `references/source-acquisition.md` | Before acquiring or extracting source bytes | yes |
| `references/dependencies.md` | Before acquiring or extracting source bytes | yes |
| `references/run-workspace.md` | Before acquiring or extracting source bytes | yes |
| `references/evidence.md` | Before the first traversal node | yes |
| `references/anti-patterns.md` | Before the first traversal node | yes |
| `references/definition-of-done.md` (re-read) | Before final verification | yes |
| `references/evidence.md` (re-read) | Before final verification | yes |

Not selected, therefore not read: `references/pdf.md`, `references/docx.md`,
`references/html.md`, `references/lengthy-markdown.md`, `references/oai-native.md`,
`references/failure-recovery.md`, `modules/debugging-document-workflows.md`,
`modules/recovering-document-workflows.md`. The source is a small Markdown file, no node
failed, and no recovery path was entered.

## Helper help read before first use

| Helper | Command | Read |
|---|---|---|
| `scripts/extract_markdown.py` | `--help` | yes |
| `scripts/inspect_chunks.py` | `--help` | yes |
| `scripts/build_evidence.py` | `--help` | yes |
| `scripts/traversal_report.py` | `--help` | yes |
| `scripts/verify_run.py` | `--help` | yes |

## Preflight flags

```json
{
  "skill_read": true,
  "required_references_read": true,
  "helper_help_read": true,
  "runtime_profile_resolved": true,
  "traversal_plan_ready": true
}
```
