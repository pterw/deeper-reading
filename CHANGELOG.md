# Changelog

## Unreleased

- HTML: text after an unclosed or mismatched heading is no longer lost. Words in
  table cells, at `<br>` and in `<pre>` no longer merge, and table and `<pre>`
  blocks end with one newline.
- DOCX: text boxes are read once, field instructions no longer leak into the
  text, and deleted, inserted and moved text is kept with `[deleted: ...]` /
  `[inserted: ...]` markers.
- Markdown: a fence closes only on a matching closer. One-column and one-dash
  tables are tables, `## Using C#` keeps its `#`, and fence and table blocks no
  longer glue to the next line.
- Extraction exits 1 with a "no extractable text" message when a source yields
  no text at all, instead of writing an empty manifest. PDFs without a text
  layer point at OCR (the `oai-native` profile).

### Compatibility

- Run folders made with 0.2.3 for HTML, DOCX or Markdown sources whose extraction
  changed fail reproduction until the source is re-extracted (chunk text, ids and
  hashes change).

## 0.2.3 - 2026-11-07

Combines the v0.2.2 structured-verification work with installer and script
hardening. It is the first release on npm (`npx deeper-reading`), and on GitHub
Releases with the distribution ZIP and its SHA-256.

- Shared Python/Node transaction locks cover ownership reads, staging,
  replacement, discovery, receipts, rollback, cleanup and uninstall.
- Discovery requires an exact enabled skill record; failed processes and
  unsupported output formats produce diagnostics rather than false verification.
- Structured findings preserve `validate_run() -> list[str]` compatibility and
  add stable `codes` to `dod.json`. CLI verification uses one findings pass.
- PDF manifests carry backend/version/capability provenance, checked against
  the run ledger and fresh extraction. Page boundaries and empty-page order are
  preserved. Committed plain/encrypted fixtures replace the reportlab-dependent test.
- Output writes are atomic, reject input collisions, and guard run-root symlink
  escapes. Invalid ledger shapes, including JSON null, fail diagnostically.
- README reorganized around installation, commands, artifacts, and actual limits.
- ZIP builds use a defined runtime/installer inventory and atomic publication;
  private worktree files, old archives and source-overwriting outputs are excluded.

### Compatibility

- Regenerate pre-0.2.3 PDF manifests and their evidence; chunk boundaries changed
  and PDF ledgers now require the emitted `extraction` object.
- Copilot discovery needs `skill list --json`; unsupported older versions fail
  discovery. Gemini uses the documented list-record format.
- Old installers do not cooperate with the new lock. Never run mixed old/new
  installers against one target. Interrupted locks require deliberate recovery.
- PDF encryption is tested at extraction; the final verifier cannot receive a
  password. No OCR or layout-verification capability is added.

### Deferred from the exploratory v0.2.2 plan

- Building a new stdlib PDF parser is not part of this release. A synthetic
  fixture writer is not evidence that a general PDF reader is feasible.
- The findings catalogue is populated and checked against source declarations;
  exhaustive executed coverage of every individual finding code remains a
  separate test-coverage task. Existing mutation tests and new regression tests
  cover the demonstrated failures; no universal parser/security guarantee is claimed.
