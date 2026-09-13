# deeper-reading

**Exhaustive document traversal and anti-skimming for agentic workflows.**

[![Release](https://img.shields.io/github/v/release/pterw/deeper-reading?color=blue&style=flat-square)](https://github.com/pterw/deeper-reading/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/pterw/deeper-reading/ci.yml?branch=main&style=flat-square)](https://github.com/pterw/deeper-reading/actions)
[![Tests](https://img.shields.io/badge/tests-270%20passed-brightgreen?style=flat-square)](tests/)
[![Spec](https://img.shields.io/badge/spec-agentskills.io-8a2be2?style=flat-square)](https://agentskills.io)
[![Dependencies](https://img.shields.io/badge/dependencies-zero%20external-success?style=flat-square)](references/dependencies.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

`deeper-reading` exists to stop language-model agents from doing the thing they are naturally tempted to do with dense technical material: skim, find the first plausible match, produce a high-level summary, and declare the job finished.

It was born out of frustration with exactly that failure mode while reading dense mechanistic-interpretability work such as Anthropic's Jacobian Space paper, where a useful answer depends on details scattered across proofs, caveats, appendices, overrides, and later sections—not merely on finding one paragraph that looks relevant.

The core product is **not chunking**.

Chunking is the mechanical ruler.

The product is a workflow in which an agent cannot reach **Done** until the entire source has been traversed and every canonical chunk has a fresh, verified evidence verdict.

---

## The guarantee

For a source that deterministically emits 12 chunks:

```text
source
  ↓
canonical extractor
  ↓
12 canonical chunks
  ↓
chunk 1  → evidence / explicit non-match → verified
chunk 2  → evidence / explicit non-match → verified
chunk 3  → evidence / explicit non-match → verified
...
chunk 12 → evidence / explicit non-match → verified
  ↓
reproduce canonical chunk universe from source bytes
  ↓
verify evidence ledger + traversal events + source fidelity
  ↓
Done
```

Finding the answer in chunk 4 does **not** make chunks 5–12 disappear.

A forged 4-chunk manifest does not help either: the verifier re-runs the bundled extractor against the bound source bytes and reproduces the canonical chunk universe before accepting completion.

The workflow is deliberately hostile to:

- first-plausible-match exits;
- needle-in-a-haystack retrieval masquerading as reading;
- high-level summaries standing in for full traversal;
- silently skipped appendices or later sections;
- stale or hand-edited evidence manifests;
- "I found what I needed" premature completion;
- broad retries that discard already-verified work;
- moving past a failed node without debugging it.

---

## When to use it

Use this skill when **coverage matters more than speed of first retrieval**.

Good fits include:

- long technical papers;
- mechanistic-interpretability papers with important late-section caveats;
- standards and RFCs;
- research appendices;
- specifications;
- compliance documents;
- contracts and policy manuals;
- long Markdown design documents;
- large implementation plans;
- audit/reconciliation work;
- source-review tasks where you need to prove what was actually traversed;
- PDF/DOCX/HTML workflows where layout or extraction failures can silently change meaning.

It is especially useful when the dangerous failure mode is:

> "The agent found something plausible early, summarized it, and never proved it read the rest."

For short, obvious documents where exhaustive coverage adds no value, this workflow may be overkill.

---

## What it is *not*

This is **not**:

- a generic summarizer;
- semantic search with extra ceremony;
- a retrieval-augmented "find the relevant paragraph" tool;
- a replacement for PDF visual/layout inspection;
- a reason to trust extracted text over the source;
- a wrapper that silently downgrades document fidelity.

For PDF and DOCX, exhaustive text traversal and visual/structural QA remain separate predicates. A text extractor can prove traversal of extracted text; it cannot magically prove that a chart, equation, field, comment, or layout rendered correctly.

---

## What is a chunk?

A **chunk** is a deterministic unit of extracted source text emitted by one of the bundled extractors and recorded in `evidence/chunk-manifest.json` for a compliant run. It is not a model summary. Each chunk carries a stable chunk ID, traversal ordinal, format-specific locator, normalized byte offsets, a content hash, and an `oversize_atomic` flag when an indivisible structure must exceed the nominal size target.

The same chunk ID is referenced by `evidence/chunk-manifest.json`, `evidence/chunk-evidence.json`, `chunk_verified` events, and the user-visible `deliverables/TRAVERSAL_REPORT.md`. That shared identity is what lets the verifier prove that every canonical unit was traversed rather than merely sampled.

Format locators preserve useful source structure: PDF chunks retain page identity, DOCX chunks retain OOXML part/block context, HTML chunks retain heading/structural context, and Markdown chunks retain heading paths while keeping fenced code and tables atomic.

# How it works

The workflow combines five things:

1. **Deterministic extraction**
2. **Canonical chunk manifests**
3. **Atomic evidence per chunk**
4. **A state machine that rejects early exit**
5. **Fresh Definition-of-Done verification**

The high-level path is:

```text
START
  ↓
resolve standalone runtime + document profile
  ↓
read package-owned workflow modules
  ↓
write traversal plan
  ↓
extract source → canonical chunks.json
  ↓
traverse one bounded chunk/node at a time
  ↓
every chunk gets:
    evidence
    OR explicit non_match
  ↓
one chunk_verified event per chunk
  ↓
failure?
  ├─ no  → continue
  └─ yes → node_failed
            → failure_diagnosed
            → repair/re-chunk failed unit only
            → architecture_stop if recovery is exhausted
            → paths_exhausted + disclosure
            → alternative_designed
            → plan_revised
  ↓
re-extract original source
  ↓
reproduce canonical chunk universe
  ↓
verify chunk-evidence.json
  ↓
generate deterministic TRAVERSAL_REPORT.md
  ↓
verification_started → verification_passed
  ↓
scripts/verify_run.py PASS
  ↓
DONE
```

---

# Evidence model

The anti-skimming contract is built around three artifacts.

## `chunks.json`

Produced by a bundled extractor.

This is the **canonical chunk universe** for the bound source bytes.

Each chunk carries stable identity and source-location information such as:

- ordinal;
- chunk ID;
- format-specific locator;
- extracted-text byte offsets;
- content hash;
- source hash;
- extraction parameters.

The supplied manifest is **not trusted merely because its hashes are internally consistent**. Final verification re-runs the bundled extractor against the original source and compares the reproduced universe.

## `chunk-evidence.json`

This is the machine evidence ledger.

Every canonical chunk must have **exactly one** verdict:

### Evidence

Atomic assertions or constraints extracted directly from the source chunk and bound to byte ranges.

```json
{
  "chunk_id": "html-000004-...",
  "outcome": "evidence",
  "assertions": [
    {
      "text": "exact source assertion",
      "chunk_byte_start": 128,
      "chunk_byte_end": 150
    }
  ]
}
```

### Non-match

The chunk was still traversed and checked, but contains no material evidence for the requested analysis.

```json
{
  "chunk_id": "html-000005-...",
  "outcome": "non_match",
  "reason": "No material claim relevant to the requested analysis."
}
```

The ledger is intentionally **extractive**, not an abstractive mini-summary layer.

## `TRAVERSAL_REPORT.md`

A deterministic human-readable ledger generated from the canonical manifest and machine evidence.

It maps each chunk to:

- chunk ID;
- page/section/heading locator;
- `evidence` or `non_match`;
- atomic verified assertion(s), constraint(s), or reason.

This is the thing you can actually skim as a human when you want proof of coverage.

---

# Supported source types

The portable runtime payload bundles extraction tools rather than assuming `/home/oai/skills/...` exists.

| Format | Bundled extractor | Strategy |
|---|---|---|
| PDF | `scripts/extract_pdf.py` | page-located text chunks |
| DOCX | `scripts/extract_docx.py` | structural document chunks |
| HTML | `scripts/extract_html.py` | heading-aware structural blocks |
| Markdown | `scripts/extract_markdown.py` | AST-like heading structure with atomic fences/tables |

Markdown splitting follows `#`, `##`, and `###` structure while keeping fenced code blocks and Markdown tables atomic. Oversized atomic blocks remain intact rather than being split just to satisfy a nominal chunk-size target.

## Extractor capability matrix

The traversal and evidence contract is identical for all four formats: one canonical manifest, exactly one byte-anchored verdict per chunk, ordered `chunk_verified` events, one deterministic `TRAVERSAL_REPORT.md`, one `verify_run.py` pass. What differs is extraction depth -- and the package fails closed rather than silently degrading.

| Format | Backend | Heading provenance | Atomic structures | Standalone limits |
|---|---|---|---|---|
| Markdown | pure stdlib | H1-H6 | fenced code blocks, tables | none beyond text traversal |
| HTML | pure stdlib (`html.parser`) | H1-H6 | tables, `<pre>`; drops `script`/`style`/`noscript`/`template` | no CSS, generated content, or figure interpretation |
| DOCX | pure stdlib (`zipfile` + ElementTree) | Heading1-Heading6 | -- | no layout, tracked changes, comments, or field values |
| PDF | external backend required | page locators | -- | text only: no OCR for scanned pages, no equations/figures; encrypted files need `--password` |

PDF is the one format that needs an external text backend (`pypdf`, `pymupdf`, `pdfplumber`, or the `pdftotext` binary), auto-detected in that order. When no backend exists the extractor fails closed with a named error instead of degrading silently. For PDF/DOCX visual fidelity, use the runtime's resolved visual/structural QA capabilities in addition to text traversal, and record what the backend actually proved in `evidence/format-qa.md`.

---

# Installation & Quick Start

## npm CLI (recommended)

Install the command-line package:

```bash
npm install -g deeper-reading
```

This installs the CLI package only. It does not write to an Agent Skills directory. Inspect the resolved target and runtime state without mutation:

```bash
npx deeper-reading doctor --target auto --scope user --json
```

Install the skill only with the explicit command:

```bash
deeper-reading install --target auto --scope user --json
```

No global install yet? `npx` runs the packaged CLI directly, and the npm package carries the full manifest-owned payload -- so this single call installs the skill without any lifecycle hook:

```bash
npx deeper-reading install --target auto --scope user --json
```

The Node installer itself uses Node.js 20 or newer and does not require Python. The installed extraction and verification scripts require Python 3.10 through 3.13. The npm package has no lifecycle hook that writes into an Agent Skills directory. The existing Python installer remains supported; see [Standalone Installer Usage](installer/USAGE.md).

| Command | Purpose |
| :--- | :--- |
| `doctor` | Report target, package, document-profile, and Python runtime readiness without mutation. |
| `install` | Install the manifest-owned payload transactionally; add `--dry-run` to preview. |
| `verify` | Re-hash installed files and verify receipt, discovery, and runtime readiness. |
| `uninstall` | Remove receipt-owned files; add `--force` only to remove modified managed files. |

All commands accept `--target`, `--scope`, `--document-profile`, and `--json`. Project scope accepts `--project-dir PATH` and defaults it to the current directory. Blocked or failed operations exit with status 2. Use `--help` or `<command> --help` for the complete option list.

## Python installer

### One-command automatic installation

Clone the repository and run the auto-detecting installer wrapper:

* **macOS / Linux / WSL / Git Bash:**
  ```bash
  git clone https://github.com/pterw/deeper-reading.git
  ./deeper-reading/installer/install.sh install --target auto --scope user
  ```

* **Windows PowerShell:**
  ```powershell
  git clone https://github.com/pterw/deeper-reading.git
  .\deeper-reading\installer\install.ps1 install -target auto -scope user
  ```

The installer automatically detects your active agent harness (`claude`, `gemini`, `copilot`, or `codex`) and installs the skill transactionally with atomic rollback protection.

---

### 2. Multi-Runtime Installation Matrix

If you prefer to install for a specific agent runtime or scope:

| Target Platform | Scope | Installation Command |
| :--- | :--- | :--- |
| **Claude Code** | Global (`~/.claude/skills/`) | `python installer/install.py install --target claude --scope user` |
| **Claude Code** | Project (`.claude/skills/`) | `python installer/install.py install --target claude --scope project --project-dir .` |
| **Gemini / Antigravity** | Global (`~/.agents/skills/`) | `python installer/install.py install --target gemini --scope user` |
| **Cursor** | Project (`.agents/skills/`) | `python installer/install.py install --target generic-agents --scope project --project-dir .` |
| **GitHub Copilot CLI** | Global (`~/.copilot/skills/`) | `python installer/install.py install --target copilot --scope user` |
| **Universal / Codex** | Global (`~/.agents/skills/`) | `python installer/install.py install --target generic-agents --scope user` |

---

### 3. Installer Commands & Lifecycle

The built-in installer is a full-featured package manager:

* **Preflight Inspection (`doctor`)**:
  Inspect your runtime, detect tools, and check extractor readiness safely without writing files:
  ```bash
  python installer/install.py doctor --target auto --json
  ```

* **Dry-Run Mode**:
  Preview the exact transaction before applying:
  ```bash
  python installer/install.py install --target auto --scope user --dry-run
  ```

* **Cryptographic Verification (`verify`)**:
  Audit installed payload files against the manifest and receipt hashes to detect corruption:
  ```bash
  python installer/install.py verify --target auto --scope user --json
  ```

* **Safe Uninstallation (`uninstall`)**:
  Cleanly remove the skill; only deletes receipt-owned files while preserving user notes:
  ```bash
  python installer/install.py uninstall --target auto --scope user
  ```

---

# How to call the skill

Agent Skills hosts can discover skills automatically, but for high-stakes reading tasks it is useful to name the skill explicitly so your intent is unambiguous.

A simple host-neutral pattern is:

> **Use `deeper-reading` to exhaustively read this source. Do not stop after finding the first relevant passage. Traverse and verify every canonical chunk before answering.**

## Example: technical paper

> Use `deeper-reading` to read this paper exhaustively. I care about the authors' actual mechanistic claims, proofs, caveats, limitations, and any later sections that qualify earlier statements. Do not give me a summary until every canonical chunk has a verified evidence verdict.

## Example: narrow question without narrow traversal

> Use `deeper-reading` to answer: "What does this paper claim about internal conflict under forced behavior?" The question is narrow, but traversal is not. Read and verify the complete paper so later caveats or overrides cannot be skipped.

## Example: long specification

> Use `deeper-reading` on `SPEC.md`. Extract every requirement, invariant, exception, and override. Preserve code fences and tables atomically. Produce the final answer only after the complete traversal ledger passes verification.

## Example: audit / reconciliation

> Use `deeper-reading` to reconcile these documents. Every chunk in every source must have an evidence or explicit non-match verdict. Surface contradictions with exact source locators and do not silently collapse conflicting requirements.

## Example: proof artifact requested

> Use `deeper-reading` and include `TRAVERSAL_REPORT.md` with the final result so I can inspect which chunks produced evidence and which were explicit non-matches.

---

# Running the portable extractors directly

The skill normally orchestrates these for you, but each extractor is standalone.

Always check current CLI help first:

```bash
python scripts/extract_pdf.py --help
python scripts/extract_docx.py --help
python scripts/extract_html.py --help
python scripts/extract_markdown.py --help
```

## PDF

```bash
python scripts/extract_pdf.py paper.pdf --out chunks.json
```

Optional backend selection:

```bash
python scripts/extract_pdf.py paper.pdf \
  --out chunks.json \
  --backend pypdf
```

## DOCX

```bash
python scripts/extract_docx.py specification.docx --out chunks.json
```

## HTML

Acquire and preserve the source HTML bytes first, then bind provenance with `--source-uri`:

```bash
python scripts/extract_html.py paper.html \
  --out chunks.json \
  --source-uri "https://example.org/canonical-paper"
```

## Markdown

```bash
python scripts/extract_markdown.py DESIGN.md --out chunks.json
```

---

# Generate the traversal report

After creating `chunk-evidence.json`:

```bash
python scripts/traversal_report.py \
  chunks.json \
  chunk-evidence.json \
  --out TRAVERSAL_REPORT.md
```

The report is derived from machine evidence. Hand-editing it does not change the authoritative ledger.

---

# Verify Definition of Done

```bash
python scripts/verify_run.py \
  /path/to/run/run.json \
  --write-dod /path/to/run/dod.json
```

Exit code `0` means the machine-checkable traversal predicates passed.

That includes reproducing the canonical chunk universe from the original bound source rather than blindly trusting the supplied manifest.

It does **not** waive required visual/structural QA for PDF/DOCX content that cannot be proven from extracted text alone.

---

# Finding your deliverables

Every substantial run emits all proof into one **run root** -- the folder the traversal names as its output boundary. One document, one run root; a new document means a new folder. Nothing is ever written outside it.

```text
<run-root>\
├── run.json                          <- the run ledger; binds every path below
├── plan.md                           <- the pre-committed traversal plan
├── dod.json                          <- verifier-written predicates (passed/violations)
├── deliverables\                     <- START HERE
│   ├── TRAVERSAL_REPORT.md           <- chunk-by-chunk proof ledger (human-readable)
│   ├── PLAN_AUDIT_FINDINGS.md        <- the requested audit/ADR, traceable to chunks
│   └── FINAL_VERIFICATION.md         <- hash-bound proof contract
└── evidence\
    ├── chunk-manifest.json           <- canonical chunk universe
    ├── chunk-evidence.json           <- one verdict per chunk, schema v2
    ├── skill-preflight.md            <- preflight booleans + phase receipts
    ├── source-manifest.md            <- bound source identity
    ├── failure-ledger.md             <- failure_diagnosed records
    ├── format-qa.md                  <- declared QA rows
    └── verification-log.txt          <- fresh proving commands
```

`deliverables/TRAVERSAL_REPORT.md` is the human-readable proof: grouped by canonical chunk, with the locator and every atomic assertion nested beneath it. It is rendered from the machine evidence pair and rejected if hand-edited.

## The proof contract

`deliverables/FINAL_VERIFICATION.md` records the run root inside itself, the source SHA-256, the chunk and verdict counts, and a SHA-256 digest of every emitted artifact. Anyone can re-prove the run with one command from the deeper-reading root:

```bash
python scripts/verify_run.py /path/to/run/run.json
```

The verifier re-extracts the source, requires the reproduced chunk universe to match exactly, re-hashes every chunk against its `content_sha256`, regenerates `TRAVERSAL_REPORT.md` and requires byte equality, then rewrites `dod.json`. Exit 0 with all declared deliverables present is the passing state.

A completed reference run ships with the repository at `tests/fixtures/deepseek-first-run/` (70 chunks, 192 assertions) and the meta-test pattern is documented in `installer/USAGE.md`.

---

# Runtime profiles

The skill has one canonical standalone profile and one optional native enhancement profile.

## `standalone`

Canonical/default on every supported Agent Skills host. It uses the bundled PDF, DOCX, HTML, and Markdown extractors plus the package-owned planning, execution, debugging, recovery, and verification modules. No external process framework is required.

## `oai-native`

Optional enhancement for the OpenAI/ChatGPT harness where live internal document skills exist. It may add `/home/oai/skills/pdfs`, `/home/oai/skills/docx`, richer rendering, OCR, and layout inspection. It may never replace or redefine the canonical standalone anti-skimming chunk/evidence contract.

---

# Failure behavior

A failed node does **not** authorize the agent to wander to a sibling branch.

The binding sequence is:

```text
node_failed
  ↓
failure_diagnosed
  ↓
repair or re-chunk only the failed unit
  ↓
node_recovered or node_rechunked
  ↓
continue
```

If bounded recovery paths are exhausted:

```text
architecture_stop
  ↓
paths_exhausted
  ↓
disclosure
  ↓
alternative_designed
  ↓
plan_revised
  ↓
resume execution
```

Already-verified upstream work stays verified.

---

# Repository layout

```text
deeper-reading/
├── package.json
├── SKILL.md
├── VERSION
├── MANIFEST.json
├── references/
│   ├── anti-patterns.md
│   ├── control-flow.md
│   ├── definition-of-done.md
│   ├── deliverable.md
│   ├── dependencies.md
│   ├── docx.md
│   ├── evidence.md
│   ├── failure-recovery.md
│   ├── html.md
│   ├── lengthy-markdown.md
│   ├── pdf.md
│   ├── prerequisites.md
│   ├── runtime-profiles.md
│   └── source-acquisition.md
├── scripts/
│   ├── chunk_common.py
│   ├── extract_pdf.py
│   ├── extract_docx.py
│   ├── extract_html.py
│   ├── extract_markdown.py
│   ├── traversal_report.py
│   └── verify_run.py
├── installer/
│   ├── node/
│   │   ├── adapters.js
│   │   ├── cli.js
│   │   ├── core.js
│   │   ├── manifest.js
│   │   └── prerequisites.js
│   ├── install.py
│   ├── install.sh
│   ├── install.ps1
│   ├── core.py
│   ├── distribution.py
│   ├── manifest.py
│   ├── prerequisites.py
│   ├── USAGE.md
│   └── adapters/
└── tests/
  ├── node/
  └── npm/
```

`SKILL.md` remains the canonical Agent Skill entrypoint at the package root.

---

# Design principles

### Exhaustive traversal over retrieval

A narrow question does not imply a narrow read.

### Source over derivative

The original source is authoritative. Extracted text is evidence infrastructure, not a replacement for the source.

### Evidence before completion

"Looks done" is not a terminal state.

### Local failure isolation

Retry or re-chunk the failed unit, not the entire corpus.

### Atomic evidence over summaries

Evidence should preserve exact assertions and locations rather than create a second lossy abstraction layer.

### Portable without pretending all runtimes are identical

Runtime-specific capabilities are explicit and verified.

---


# Future scope

Future adapters may extend the same exhaustive-traversal invariant to **XLSX** and **CSV** by defining deterministic row/cell/table chunk universes. An already-verified canonical chunk universe may also be used to **rebuild derived representations** for navigation or analysis, but those derived views must never replace traversal of the bound source.

# Why this exists

Long-context models are very good at producing plausible answers from partial evidence.

That is exactly the problem.

A 20-page paper can contain the answer on page 6, the caveat on page 14, and the methodological limitation in an appendix. A 3,000-line specification can define a rule near the top and override it two headings later. A model that retrieves the first useful passage may sound completely convincing while never encountering the text that changes the answer.

`deeper-reading` turns "read the whole thing" from a conversational request into a machine-checkable workflow invariant.

**Read it. Chunk it. Prove every chunk. Then—and only then—Done.**

---

# License

MIT. See [`LICENSE`](LICENSE).

## v0.2.1 phase-gated reference loading

References now load at the lifecycle gate that requires them instead of all at activation. The root `SKILL.md` keeps lifecycle order and routes to the bundled module for the current state; each module owns the references and helper guidance for its own boundary -- activation and contract establishment, planning, extraction, traversal, failure diagnosis and recovery, and verification -- and loads them before its gate.

Phase receipts are recorded in `evidence/skill-preflight.md`. `required_references_read` remains the final compatibility aggregate over those receipts.

The v0.2.0 machine evidence contract is unchanged: `run.json`, `dod.json`, event names, manifest and evidence schemas, verifier predicates, canonical chunk construction, and source-bound assertions all behave as before.

## v0.2 hardening and evidence substrate

The hardened runtime keeps the same core invariant—complete source traversal, one verified verdict per canonical chunk, and fresh re-extraction before Done—while tightening the boundaries that proof depends on.

Installer receipts are untrusted input. Every **receipt-owned** payload path must remain inside the resolved **install root** before hashing, pruning, verification, or deletion; `force=True` never bypasses containment. HTML extraction retains every non-skipped DOM text node exactly once outside `script`, `style`, `noscript`, and `template`, while Markdown/HTML use H1-H6 heading provenance and DOCX recognizes Heading1 through Heading6.

Existing evidence **schema v1 remains accepted**. `scripts/build_evidence.py` emits **schema v2** atoms with deterministic `atom_id` values. A unique exact quote can bind automatically; an ambiguous repeated quote requires an explicit byte span, which must reproduce the exact UTF-8 source bytes. These IDs identify extractive spans—they do not prove semantic truth or model comprehension.

`TRAVERSAL_REPORT.md` is now grouped by canonical chunk for human auditability: run summary, chunk index, then one detail block per canonical chunk with its atoms nested beneath it. For bounded source inspection, `scripts/inspect_chunks.py MANIFEST --summary` and `--from N --to M` provide a read-only view over the same canonical manifest.
