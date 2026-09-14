# deeper-reading

Exhaustive document traversal and source-bound evidence for agent workflows.

[![CI](https://img.shields.io/github/actions/workflow/status/pterw/deeper-reading/ci.yml?branch=main)](https://github.com/pterw/deeper-reading/actions)
[![Release](https://img.shields.io/github/v/release/pterw/deeper-reading)](https://github.com/pterw/deeper-reading/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

`deeper-reading` is an Agent Skill for work where missing a late caveat, appendix,
or override would change the answer. It requires a traversal plan, a verdict for
every canonical chunk, and fresh verification before the agent declares Done.

The verifier checks source identity, reproduced extraction, exact evidence spans,
coverage, event order, and declared completion conditions. Those checks do **not**
prove that a model understood the source or that an extracted claim is true.

## Install

The npm installer needs **Node.js 20+**. Running the installed document scripts
needs **Python 3.10–3.13**. PDF extraction also needs a supported text backend;
HTML, Markdown and DOCX extraction use the Python standard library.

```sh
npx deeper-reading doctor --target auto --json
npx deeper-reading install --target auto --scope user --dry-run --json
npx deeper-reading install --target auto --scope user --json
```

Installing the npm package alone does not install the Agent Skill. Only the
explicit `install` command writes to a skill directory; there are no npm install
hooks that do so. To try the current checkout instead of a published package:

```sh
node installer/node/cli.js doctor --target generic-agents --json
node installer/node/cli.js install --target generic-agents --scope project --project-dir . --json
```

The Python installer is also supported:

```sh
python installer/install.py doctor --target generic-agents --json
python installer/install.py install --target generic-agents --scope user --json
```

Choose `generic-agents`, `copilot`, `gemini`, `codex`, or `claude`. `auto` checks
for available commands in Copilot → Gemini → Codex → Claude order, then uses
`generic-agents`; it does not identify which host is currently running you.
Use `--scope project --project-dir PATH` for a specific project.

| Command | Purpose |
| --- | --- |
| `doctor` | Inspect package and runtime readiness without installing. |
| `install` | Copy the manifest-owned payload; `--dry-run` previews it. |
| `verify` | Recheck installed files, receipt and declared readiness. |
| `uninstall` | Remove receipt-owned files while preserving unowned files. |

Use each command's `--help` for its accepted options. `--force` on uninstall
allows removing modified owned files; it never bypasses containment in the
resolved install root. Installation verification checks recorded discovery
state, not a fresh semantic assessment of the host.

Both installers share a per-target lock across install, upgrade and uninstall,
including rollback and cleanup. Contention fails clearly; retry after the active
operation finishes. Older installers do not honor the lock. See
[installer usage](https://github.com/pterw/deeper-reading/blob/main/installer/USAGE.md) for paths, interrupted-lock recovery,
discovery formats and compatibility requirements.

## Supported formats and limits

| Format | Extraction | Locators and boundaries | Requires separate QA |
| --- | --- | --- | --- |
| Markdown | Standard library | H1–H6 heading paths; fenced code and tables stay atomic | Rendered meaning, linked material |
| HTML | Standard-library HTML parser | Heading/structural context; tables and preformatted text stay atomic | CSS, scripts, generated content, figures |
| DOCX | Standard-library ZIP + OOXML parsing | Document/story parts, Heading1–Heading6, paragraphs and tables | Layout, revision meaning, field evaluation, visual fidelity |
| PDF | Optional text backend | Ordered page locators; empty pages remain represented | OCR, graphics, equations and visual layout |

PDF backends are detected in this order: `pypdf`, `PyMuPDF`, `pdfplumber`, then
`pdftotext`. To choose the declared optional Python backend, install
[requirements-optional.txt](https://github.com/pterw/deeper-reading/blob/main/requirements-optional.txt) in your environment. An existing pdftotext executable
also works. No backend is installed automatically.

The shipped PDF adapters return text only. A library having layout features
does not mean this extraction path proves layout. See [PDF guidance](references/pdf.md)
and [dependency resolution](references/dependencies.md).

## What is a chunk?

A chunk is a deterministic unit of extracted text, recorded in
`evidence/chunk-manifest.json`. Each has a chunk ID, ordinal, locator, UTF-8 byte
span and content hash. The offsets identify canonical extracted text, not byte
positions in a PDF or DOCX container. Oversized atomic code/table blocks remain
intact and are marked explicitly.

A manifest with 12 chunks requires 12 verdicts: either exact extractive evidence
or an explicit `non_match` reason. Finding a useful answer in chunk 4 does not
remove chunks 5–12. The verifier re-extracts the original bound file and compares
the resulting manifest, so a smaller self-consistent manifest is insufficient.

Evidence schema v1 remains accepted. `build_evidence.py` produces schema v2:
exact quotes with deterministic `atom_id` values. Repeated quotes need explicit
byte spans. An atom identifies an extractive span; it does not certify truth.

## Run the workflow

The installed `SKILL.md` routes the agent through the package-owned phases:

```text
establish source and fidelity contract → plan → extract → traverse every chunk
→ resolve failures → produce requested deliverable → fresh verification
```

References load at their required phase rather than all at activation. The agent
records phase receipts in `evidence/skill-preflight.md`; final verification still
requires the aggregate preflight contract. A failed node must be diagnosed before
execution continues. Recovery preserves already verified work and follows the
[documented failure protocol](references/failure-recovery.md).

From the package root, inspect helper `--help` before use. For example:

```sh
python scripts/extract_markdown.py source.md --run-root runs/review
python scripts/inspect_chunks.py runs/review/evidence/chunk-manifest.json --summary
python scripts/inspect_chunks.py runs/review/evidence/chunk-manifest.json --from 1 --to 3
```

Author an exact evidence/non-match verdict for every chunk, then bind and render:

```sh
python scripts/build_evidence.py runs/review/evidence/chunk-manifest.json draft.json --out runs/review/evidence/chunk-evidence.json
python scripts/traversal_report.py --run-root runs/review
python scripts/verify_run.py runs/review/run.json
```

These commands are individual tools, not an automatic end-to-end run generator.
The agent must also create the plan, run ledger, event records, required QA
evidence and requested deliverables described in [the evidence contract](references/evidence.md).
Extraction or report generation alone does not establish completion.

## Find the deliverables

One document uses one run root. A typical layout is:

```text
run-root/
├── run.json
├── plan.md
├── dod.json
├── deliverables/
│   ├── TRAVERSAL_REPORT.md
│   └── requested-analysis.md
└── evidence/
    ├── chunk-manifest.json
    ├── chunk-evidence.json
    ├── skill-preflight.md
    ├── source-manifest.md
    ├── failure-ledger.md
    ├── format-qa.md
    └── verification-log.txt
```

Start with the requested analysis and `TRAVERSAL_REPORT.md`, grouped by canonical
chunk. `dod.json` records `passed`, named `predicates`, human `violations`, and
stable finding `codes`. `verify_run.py` writes that file and exits 0 only when its
checks pass; failures exit nonzero. The report is derived from machine evidence
and checked against the deterministic rendering.

The CLI guards against overwriting its inputs, writes complete output artifacts
atomically, and checks run-root output containment. Optional human verification
notes are useful, but the verifier does not automatically generate or certify an
all-artifact digest report called `FINAL_VERIFICATION.md`.

## PDF provenance and migration

Copy the PDF manifest's `extraction` object into the run ledger. It names the
backend and installed version, `format: "pdf"`, and `capabilities: ["text"]`.
Final verification compares this with independently reproduced extraction and
surfaces it in `dod.json`. Unknown backends, mismatched provenance and unsupported
OCR claims fail verification.

PDF manifests from before 0.2.3 require regeneration with their evidence: page
boundaries and backend provenance are now explicit. Changing backend or version
can change extraction. `--password` supports encrypted extraction, but final
verification has no password input; see [runtime profiles](references/runtime-profiles.md)
for that limitation. The new fixture includes text, a table, an empty page and an
encrypted variant, with [recorded source hashes](https://github.com/pterw/deeper-reading/blob/main/tests/fixtures/pdf-first-run/README.md).

`standalone` is the default profile and owns the traversal contract. `oai-native`
is an optional enhancement when live host-native visual/document tools exist;
it does not replace canonical text coverage or make missing capabilities pass.

## Development

```sh
python -m pytest -rs
npm test
npm run test:pack-smoke
python installer/install.py doctor --target generic-agents --json
```

Tests cover extraction, forged evidence and manifests, failure sequencing,
installer rollback, cross-language contention, discovery parsing and packed CLI
lifecycle. PDF tests use committed fixtures instead of requiring reportlab.
Optional backend and filesystem capability skips name their reason. CI exercises
the pypdf path without skips; it allows at most one missing-pdftotext skip and,
on Windows only, up to nine named symlink-capability skips. Unknown skip reasons
fail CI. The CI environment installs the declared optional backend for these tests.
The version matrix covers
Python 3.10–3.13 and Node 20/22/24 on Windows and Linux; local success is not a
claim that the remote matrix has run. See [CONTRIBUTING.md](https://github.com/pterw/deeper-reading/blob/main/CONTRIBUTING.md).

The canonical skill is `SKILL.md`; workflow modules are in `skills/`, detailed
contracts in `references/`, document tools in `scripts/`, and installation code
in `installer/`. [Release notes](https://github.com/pterw/deeper-reading/blob/main/CHANGELOG.md) record compatibility changes.

## Future scope

XLSX and CSV need explicit row/cell chunk contracts before support can be claimed.
Future consumers may rebuild derived search or graph views from verified evidence for navigation,
but cannot replace traversal of the bound source. A new stdlib PDF reader remains
exploratory work; the existing backend adapters are the supported path.

## License

MIT. See [LICENSE](LICENSE).
