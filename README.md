# deeper-reading

[![CI](https://img.shields.io/github/actions/workflow/status/pterw/deeper-reading/ci.yml?branch=main)](https://github.com/pterw/deeper-reading/actions)
[![npm](https://img.shields.io/npm/v/deeper-reading)](https://www.npmjs.com/package/deeper-reading)
[![Release](https://img.shields.io/github/v/release/pterw/deeper-reading)](https://github.com/pterw/deeper-reading/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/pterw/deeper-reading/blob/main/LICENSE)
[![Node](https://img.shields.io/node/v/deeper-reading)](https://www.npmjs.com/package/deeper-reading)
[![Python 3.10 to 3.13](https://img.shields.io/badge/python-3.10%20to%203.13-blue)](https://github.com/pterw/deeper-reading/blob/main/installer/USAGE.md)

An agent that reads a long document tends to skim it, stop at the first plausible match, or say it is done before it has read everything. `deeper-reading` is an Agent Skill: a folder of instructions and scripts that your coding agent loads on request. It splits the document into numbered chunks, requires a verdict for every chunk, and blocks Done until a verifier confirms that all of them are covered.

## What you get

Each run produces a run root: the folder that holds one document's plan, evidence and deliverables. It contains four things you can inspect:

- **A verdict for every chunk**: a chunk is a numbered piece of the extracted text. Each one gets either an exact quote or an explicit `non_match` reason, so no chunk can be skipped without a recorded verdict.
- **Exact quotes bound to bytes**: each quote points to a byte span in the extracted text, and the verifier re-extracts your original file to check it.
- **A traversal report**: `TRAVERSAL_REPORT.md` lists the verdicts grouped by chunk.
- **A completion record**: `dod.json` (Definition of Done) comes from a verifier that blocks Done until every check passes.

The skill reads Markdown, HTML, DOCX and PDF. PDF support covers text only.

## An example

This excerpt comes from a real run. The task was to read a 14-chunk Markdown plan. The agent had to list what must be true for the plan to count as finished, and to find late statements that narrow earlier ones. Each such entry in `requested-analysis.md` names both statements, quotes them, and gives the chunk ID. Entry 10 reads:

```text
10. **The freeze gate becomes an ordered sequence.**
    Earlier (chunk `markdown-000002-0935af6dec34`): "Freeze remains held until frozen-byte verification passes."
    Later (chunk `markdown-000012-1f46e1271824`): "Invoke `verification-before-completion`, hash archive, then freeze."
    The later rule fixes the order: verify, hash the archive, then freeze.
```

The verifier then wrote this line to `dod.json`, the record of whether every check passed:

```json
"passed": true
```

Passing means every chunk has a verdict and every quote in the evidence ledger matches the source bytes. The verifier does not check the wording of `requested-analysis.md`, and it does not mean the analysis is right. See [the full example run](https://github.com/pterw/deeper-reading/blob/main/docs/examples/README.md) for the whole run root and how to check it yourself.

## What it does not do

The verifier proves coverage and byte fidelity and nothing more. Four limits apply:

- **No proof of truth or understanding**: a quote can be exact and still be misread. You review the answer.
- **PDF is text only**: there is no OCR (optical character recognition), layout analysis or image reading.
- **Images are listed, not understood**: for Markdown, HTML and DOCX, the skill lists every image, SVG and diagram it finds, and the agent records a disposition for each: read with a vision tool, or not read with a reason. The verifier checks that each has a disposition, not that the agent understood it. PDF images are not listed.
- **It costs more**: it takes more time and tokens than reading the document once. Use it when missing a late caveat would change the answer.

## Install

You need Node.js 20 or later to run the installer. The installed scripts need Python 3.10 to 3.13. PDF files also need a text backend such as `pypdf`; HTML, Markdown and DOCX use the Python standard library.

Install the skill for your user account, then verify the installation:

```sh
npx deeper-reading install --target auto --scope user
npx deeper-reading verify --target auto --scope user
```

Installing the npm package does not install the skill. Only the `install` command writes to a skill folder; no npm hook does.

Run `doctor` first if you want to check readiness without changing anything:

```sh
npx deeper-reading doctor --target auto
```

The `--target` option names the agent that will load the skill: `generic-agents`, `copilot`, `gemini`, `codex` or `claude`. The `auto` value picks the first of Copilot, Gemini, Codex and Claude whose command is on your `PATH`, and falls back to `generic-agents`. It checks which commands are installed, not which agent you are using now, so pass `--target` if you have more than one.

Use `--scope project --project-dir PATH` to install into one project instead of your user account. Add `--dry-run` to `install` to preview the files.

[Installer usage](https://github.com/pterw/deeper-reading/blob/main/installer/USAGE.md) covers skill folders, uninstalling, recovery from `npx skills add`, and the Python installer.

## Use it

Start a task by naming the skill, for example: "Use deeper-reading to read this report end to end and list every exception to the refund policy." Some agents also load it when you ask for an exhaustive read of every section, but naming it is the reliable way. The agent then follows the phases in `SKILL.md`: establish the source, plan, extract, read every chunk, handle failures, write your deliverable, and run a fresh verification.

The agent does this with helper scripts from the skill folder. Extraction and chunk inspection look like this, run from the installed `deeper-reading` folder (see [skill roots](https://github.com/pterw/deeper-reading/blob/main/installer/USAGE.md#skill-roots)):

```sh
python scripts/extract_markdown.py source.md --run-root runs/review
python scripts/inspect_chunks.py runs/review/evidence/chunk-manifest.json --summary
```

After the agent writes a verdict for every chunk, it binds the evidence, renders the report and runs the verifier. The verifier exits 0 only when every check passes:

```sh
python scripts/build_evidence.py runs/review/evidence/chunk-manifest.json draft.json --out runs/review/evidence/chunk-evidence.json
python scripts/traversal_report.py --run-root runs/review
python scripts/verify_run.py runs/review/run.json
```

These scripts are separate tools, not an automatic end-to-end run. The agent also writes the plan, the run ledger, the QA notes and your deliverable. The [evidence contract](https://github.com/pterw/deeper-reading/blob/main/skills/deeper-reading/references/evidence.md) and the [failure recovery protocol](https://github.com/pterw/deeper-reading/blob/main/skills/deeper-reading/references/failure-recovery.md) describe those parts.

The scripts refuse to overwrite their input files and publish each output in one step, so a failure leaves no half-written file. The report and verifier scripts also refuse to write outside the run root.

Your results are in the run root. Read `deliverables/requested-analysis.md` for the answer, `deliverables/TRAVERSAL_REPORT.md` for the verdicts, and `dod.json` for the verifier result. The raw evidence is in `evidence/`, including `chunk-manifest.json` and `chunk-evidence.json`.

A manifest with 12 chunks requires 12 verdicts. Finding the answer in chunk 4 does not remove chunks 5 to 12, and a smaller manifest does not pass, because the verifier re-extracts the source itself.

## Formats and limits

Extraction depends on the format. Every format needs separate QA for what text extraction cannot see.

| Format | Extraction | Chunk boundaries | Needs separate QA |
| --- | --- | --- | --- |
| Markdown | Standard library | Heading paths H1 to H6; fenced code and tables stay whole | Rendered meaning, linked material, images, diagrams |
| HTML | Standard-library parser | Heading context; tables and preformatted text stay whole | CSS, scripts, generated content, images, diagrams |
| DOCX | Standard-library ZIP and OOXML (Office Open XML) parsing | Document parts, Heading1 to Heading6, paragraphs, tables | Layout, tracked-change display, field rendering, visual fidelity, images, diagrams |
| PDF | Optional text backend | Ordered page locators; empty pages stay represented | OCR, graphics, equations, visual layout |

PDF backends are tried in this order: `pypdf`, `PyMuPDF`, `pdfplumber`, then `pdftotext`. No backend is installed for you; run `python -m pip install pypdf` to add one. For provenance rules and migration of older PDF runs, see [PDF provenance and migration](https://github.com/pterw/deeper-reading/blob/main/installer/USAGE.md#pdf-provenance-and-migration).

## Links

These pages cover what this page leaves out:

- [Installer usage](https://github.com/pterw/deeper-reading/blob/main/installer/USAGE.md)
- [Contributing](https://github.com/pterw/deeper-reading/blob/main/CONTRIBUTING.md)
- [Changelog](https://github.com/pterw/deeper-reading/blob/main/CHANGELOG.md)
- [MIT license](https://github.com/pterw/deeper-reading/blob/main/LICENSE)
