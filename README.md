# deeper-reading

**Exhaustive document traversal and anti-skimming for agentic workflows.**

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

For PDF/DOCX visual fidelity, use the runtime's resolved visual/structural QA capabilities in addition to text traversal.

---

# Installation & Quick Start

### 1. One-Command Automatic Installation

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
