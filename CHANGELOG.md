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
- Verifier: a ledger with unresolved nodes or unresolved failures now fails
  before `done` is appended (`done.node.unresolved`,
  `done.failure.unresolved`); such ledgers used to pass until `done` existed.
- Verifier: any exception raised while validating a ledger now yields
  `ledger.validation.error` and rewrites `dod.json` with `passed: false` (a
  stale passing `dod.json` no longer survives); a non-object chunk `locator`
  reports `coverage.chunk.atomic_kind.missing` instead of crashing.
- Verifier: a run folder copied to another location now verifies, as long as
  `source.local_path` in `run.json` still resolves there (a path relative to the
  run folder moves with it). The extraction reproduction no longer compares the
  absolute `source.path`; the bytes stay bound by `sha256` and `size`.
- Installers (Windows): `--target copilot`, `--target gemini` and `--target auto`
  now work when the host CLI is a `.cmd` shim, in both the Python and Node
  installers. A `.cmd` or `.bat` host path containing any of `" % & | < > ^ ! ( ) , ; =` or a
  line break is refused: host discovery is reported as `failed` and the shim is
  not run.
- Installers (all platforms): host lookup searches only absolute `PATH` entries,
  in both the Python and Node installers: never the current directory, and no
  relative entry such as `bin` or `node_modules/.bin`.
- Installers: if removing the old backup fails after an upgrade has put the new
  version in place, the install stays committed instead of rolling back. The
  install result gains an additive `warnings` key naming the leftover backup to
  remove by hand.
- Installers: a corrupt install receipt (invalid JSON, not an object, or
  `payload_hashes`, `document_status` or `host_discovery` not an object) makes
  install, verify and uninstall stop with `invalid installation receipt` (exit
  2) and remove nothing.
- Node installer: `install` with an unready document profile now reports
  `state: blocked` with exit 2 and changes nothing, as the Python installer does.
- Docs: `references/evidence.md` now carries a worked first run (a one-chunk
  source, its commands, a `run.json` and a draft verdict) that a test drives
  through the real scripts to `passed: true`. The `run.json`, event and draft
  verdict shapes and the preflight receipts layout are documented, and
  `definition-of-done.md` says which proofs the verifier only checks for
  existence.
- Installers: `LICENSE` is now installed with the skill. Upgrading an existing
  install adds it as a managed file.
- Extraction: Markdown, HTML and DOCX extractors now record images, SVG,
  diagrams and embedded objects (Markdown and HTML images, Markdown links to
  image files, inline SVG, mermaid blocks and diagram fences, `<object>` and
  `<embed>`; DOCX drawings, VML images
  and OLE objects in every story part). They appear in an optional top-level
  `media` list of the manifest (`media-0001`, with chunk, kind, syntax,
  reference and alt text). Chunk text, ids and hashes do not change, and a
  manifest without media is byte-identical to before. PDF media is not
  recorded. In Markdown, media outside a closed, well-formed fenced code block
  counts, inline code and HTML comments included, so a doubtful case costs a
  `not_read` disposition. Known limits: a fence-looking line inside an HTML
  comment or `<pre>` pairs with a later fence, and brackets and parentheses
  nest one level only.
- Evidence: format QA gives every media reference a disposition in a top-level
  `media` list of the chunk evidence ledger: `read` (with the host vision tool
  and a summary) or `not_read` (with a reason). `build_evidence.py` rejects a
  draft whose list does not match the manifest, and the verifier reports
  `media.disposition.missing`, `.unknown`, `.duplicate` and `.invalid`. The
  check proves each reference has a disposition, not that the media was
  understood.
- Reports: `TRAVERSAL_REPORT.md` gains media counts and a `## Media` table when
  the manifest has media, and `inspect_chunks.py` lists each chunk's media (and
  `media:N` in `--summary`) so the ids are known before the ledger exists.

### Compatibility

- Run folders made with 0.2.3 for HTML, DOCX or Markdown sources whose extraction
  changed fail reproduction until the source is re-extracted (chunk text, ids and
  hashes change).
- Run folders whose Markdown, HTML or DOCX source holds media no longer
  reproduce from their earlier manifest: the verifier reports
  `reproduction.mismatch`, with the hint "manifest predates media recording;
  re-extract" when only the `media` list differs. Re-extract the source, add a
  `media` list of dispositions to the draft, rebuild the ledger with
  `build_evidence.py`, re-render `TRAVERSAL_REPORT.md`, and record the new
  manifest hash in `run.json` (`chunking.manifest_sha256`), then verify.
- The verifier finding codes `preflight.legacy` and `events.legacy` are removed.
  Ledgers carrying the four old preflight keys (such as `using_superpowers_read`)
  or `systematic_debugging` / `brainstorming` events now verify instead of
  failing.
- A host CLI reachable only through a relative `PATH` entry is no longer
  auto-detected by the installers. Use `--target`, or put an absolute directory
  on `PATH`.

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
