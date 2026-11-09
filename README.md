# deeper-reading

Exhaustive document traversal and source-bound evidence for agent workflows.

[![CI](https://img.shields.io/github/actions/workflow/status/pterw/deeper-reading/ci.yml?branch=main)](https://github.com/pterw/deeper-reading/actions)
[![npm](https://img.shields.io/npm/v/deeper-reading)](https://www.npmjs.com/package/deeper-reading)
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

To keep the command available, install the package globally and drop the `npx`
prefix:

```sh
npm install -g deeper-reading
deeper-reading doctor --target auto --json
deeper-reading install --target auto --scope user --dry-run --json
deeper-reading install --target auto --scope user --json
```

Run `verify` and `uninstall` the same way; see [After installing](#after-installing)
and the command table below.

Installing the npm package alone does not install the Agent Skill. Only the
explicit `install` command writes to a skill directory; there are no npm install
hooks that do so. To try the current checkout instead of a published package:

```sh
node installer/node/cli.js doctor --target generic-agents --json
node installer/node/cli.js install --target generic-agents --scope project --project-dir . --json
```

The Python installer is also supported. It is not on PyPI or npm: it needs a
checkout of this repository or the `deeper-reading-<version>.zip` asset on the
[GitHub Release](https://github.com/pterw/deeper-reading/releases). Unzip the
archive and run these commands from the extracted `deeper-reading/` folder:

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

### After installing

1. Run `verify` with the same `--target` and `--scope` you installed with, for
   example `npx deeper-reading verify --target auto --scope user --json`.
2. The skill lands in a per-target skills directory; see
   [Skill roots](https://github.com/pterw/deeper-reading/blob/main/installer/USAGE.md#skill-roots)
   for the path of each target and scope.
3. Start a task by naming the skill, for example "Use deeper-reading to read
   this report end to end", so the host loads it.
4. To remove it, run `uninstall` with the same target, scope and project directory. Only
   receipt-owned files are removed.

### Supported route and mixing installers

This project's own installers are the supported way to install the skill, and
the npm installer is the primary one. `npx skills add` is a different tool and is
not supported for this skill. Running it over an npm install replaces the skill
folder and drops its `.install-receipt.json`. An interactive run asks before it
overwrites; a run with `-y`, or one that uses the agents it detects, does not
ask. After that, `install` and `uninstall` refuse the folder with
`installer.receipt.missing` and change nothing, and `verify` fails, because they
will not touch files they cannot prove they own. Going the other
way is safe: if `npx skills add` came first, a later `install` refuses the
unmanaged folder and leaves it as it is.

To recover from `npx skills add`, remove its copy, then run `install` again.
For the `claude` target the agent name is `claude-code`; for `codex` it is
`codex`. Pass `-g` for user scope; for project scope omit it and run the command
from the project directory. If you added the skill for one agent:

```sh
npx skills remove deeper-reading -g -a claude-code -y
npx skills remove deeper-reading -g -a codex -y
```

Those are alternatives: use the line for your agent. `codex` and `generic-agents`
share `.agents/skills`, so one folder may belong to more than one agent. If you
added it for both claude-code and codex, list each agent in a single `remove`:

```sh
npx skills remove deeper-reading -g -a claude-code codex -y
```

For any other target, or if you prefer, delete by
hand: delete the skill folder `deeper-reading` for each agent; if it is a link,
remove the link itself and not its contents; never delete only the shared
`.agents` folder; then run `install` for each agent.

If `~/.claude/skills` is a link to `~/.agents/skills`, both targets resolve to
one folder. The second target is refused with `installer.owner.mismatch`, and
the message names the owner and the working command (`--target <owner>`). See
[Skill roots](https://github.com/pterw/deeper-reading/blob/main/installer/USAGE.md#skill-roots).

Both installers share a per-target lock across install, upgrade and uninstall,
including rollback and cleanup. Contention fails clearly; retry after the active
operation finishes. Older installers do not honor the lock. See
[installer usage](https://github.com/pterw/deeper-reading/blob/main/installer/USAGE.md) for paths, interrupted-lock recovery,
discovery formats and compatibility requirements.

## Supported formats and limits

| Format | Extraction | Locators and boundaries | Requires separate QA |
| --- | --- | --- | --- |
| Markdown | Standard library | H1–H6 heading paths; fenced code and tables stay atomic | Rendered meaning, linked material, images and diagrams |
| HTML | Standard-library HTML parser | Heading/structural context; tables and preformatted text stay atomic | CSS, scripts, generated content, figures, images and diagrams |
| DOCX | Standard-library ZIP + OOXML parsing | Document/story parts, Heading1–Heading6, paragraphs and tables | Layout, revision meaning, field evaluation, visual fidelity, images and diagrams |
| PDF | Optional text backend | Ordered page locators; empty pages remain represented | OCR, graphics, equations and visual layout |

For Markdown, HTML and DOCX, the manifest lists every image, SVG and diagram
reference it finds. Each one needs a disposition in the evidence ledger: read
with a host vision tool, or not read with a reason. The verifier checks that
every one has a disposition. It does not prove the media was understood. See
[evidence](skills/deeper-reading/references/evidence.md).

PDF backends are detected in this order: `pypdf`, `PyMuPDF`, `pdfplumber`, then
`pdftotext`. To choose the declared optional Python backend, run
`python -m pip install pypdf` in your environment. An existing pdftotext
executable also works. No backend is installed automatically.

The shipped PDF adapters return text only. A library having layout features
does not mean this extraction path proves layout. See [PDF guidance](skills/deeper-reading/references/pdf.md)
and [dependency resolution](skills/deeper-reading/references/dependencies.md).

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
[documented failure protocol](skills/deeper-reading/references/failure-recovery.md).

From the skill folder (the installed `deeper-reading` folder, or `skills/deeper-reading` in a checkout), inspect helper `--help` before use. For example:

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
evidence and requested deliverables described in [the evidence contract](skills/deeper-reading/references/evidence.md).
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
atomically, and checks run-root output containment.

## PDF provenance and migration

Copy the PDF manifest's `extraction` object into the run ledger. It names the
backend and installed version, `format: "pdf"`, and `capabilities: ["text"]`.
Final verification compares this with independently reproduced extraction and
surfaces it in `dod.json`. Unknown backends, mismatched provenance and unsupported
OCR claims fail verification.

PDF manifests from before 0.2.3 require regeneration with their evidence: page
boundaries and backend provenance are now explicit. Changing backend or version
can change extraction. `--password` supports encrypted extraction, but final
verification has no password input; see [PDF reference](skills/deeper-reading/references/pdf.md)
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

The canonical skill is `skills/deeper-reading/SKILL.md`; workflow modules are the `modules/<name>.md` files in that folder, detailed
contracts in `skills/deeper-reading/references/`, document tools in `skills/deeper-reading/scripts/`, and installation code
in `installer/`. [Release notes](https://github.com/pterw/deeper-reading/blob/main/CHANGELOG.md) record compatibility changes.

## Future scope

XLSX and CSV need explicit row/cell chunk contracts before support can be claimed.
Future consumers may rebuild derived search or graph views from verified evidence for navigation,
but cannot replace traversal of the bound source. A new stdlib PDF reader remains
exploratory work; the existing backend adapters are the supported path.

## License

MIT. See [LICENSE](LICENSE).
