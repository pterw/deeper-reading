# Changelog

## Unreleased

- Installer: `install` (also with `--dry-run`), `verify` and `uninstall` now
  read the receipt in the skill folder and refuse a folder that another
  target or scope installed. This can happen when a skills folder is a link.
  Before, `uninstall --target claude` through a link could delete a codex
  install. Now the command exits 2 and changes nothing. `doctor` is not
  checked.
- Installer: a project-scope folder that resolves outside its project, for
  example a `.claude` that is a link out of the project, is refused. `install`
  (also `--dry-run`) refuses it before writing anything. Such a project worked
  in 0.2.5 and can no longer install at project scope: use `--scope user` or
  a real folder in the project.
- Installer: a receipt whose target or scope is missing or unknown is
  refused. The message says to delete the skill folder.
- Installer: if `~/.claude/skills` is a link to `~/.agents/skills`, the
  second target you use on that folder is now refused. The message names the
  owning target and the command that works (`--target <owner>`). `codex` and
  `generic-agents` share a folder by design and are still allowed.
- Installer: with `--json`, a failure may now carry a `code`. The codes are
  `installer.owner.mismatch`, `installer.project.escape`,
  `installer.receipt.owner_invalid` and `installer.receipt.missing`. A failed
  `verify` now also carries `passed: false`.
- Installer: when `install` or `uninstall` finds a folder with no receipt, as
  after `npx skills add`, the refusal now carries `installer.receipt.missing`
  and says how to recover. For `claude` and `codex` it gives the
  `npx skills remove` command. Other targets get the delete route. Nothing is
  changed. `verify` keeps its existing failure, with no code.
- `README.md` says the project's own installers are the supported route, with
  npm the primary one, what `npx skills add` does to an npm install, and how
  to recover. `installer/USAGE.md` lists the ownership checks and their codes.
- Layout: the skill now lives in `skills/deeper-reading/` in the repository.
  `SKILL.md`, `VERSION`, `references/`, `scripts/` and the workflow modules
  moved there. `MANIFEST.json` names the folder in a new optional field,
  `skill.root`. The root `LICENSE` stays, and the skill folder holds a copy.
- Layout: the npm package and the release ZIP now hold the skill under
  `skills/deeper-reading/`, not at the package root. The npm package gains
  one file, the `LICENSE` copy inside the skill.
- Layout: the installed skill is unchanged. It has the same 38 files at the
  same paths, with the same hashes, as 0.2.5. A 0.2.5 install still
  verifies, upgrades and uninstalls.
- Layout: `npx skills add` on the repository finds one skill and installs
  those 38 files, not the whole repository. This is the same list as an npm
  install.
- Layout: the two repository helper skills in `.github/skills/` are marked
  internal, so `npx skills add` does not install them.
- Installer: both installers refuse a bad `skill.root` in the manifest.
  `doctor` in the Python installer now reads the manifest. It exits 2 when
  the manifest is missing or damaged. It did not read it before.

## 0.2.5 - 2026-11-08

- `README.md` is no longer installed into the skill directory, and an upgrade
  from an earlier release removes it. npm and the release ZIP still include it.
- `CONTRIBUTING.md` is no longer in the release ZIP.
- `oai-native` guidance lives in `references/oai-native.md` and is read only
  when the document profile is or becomes `oai-native`.
- `references/run-workspace.md` (the run-root layout and the `--run-root`
  extractor commands) is now read before extraction.
- Markdown: an image link whose destination uses a character reference,
  such as `[figure](plot&#46;png)`, is now recorded as media. The recorded
  reference keeps the original spelling. A destination that decodes to a
  fragment (`p&num;.png` is the file `p`) is no longer recorded as an image.
- Markdown: in raw HTML, an attribute name inside another attribute's value
  (`<div title="class=example" class="mermaid">`,
  `<img title="src=x.png" src="y.png">`) no longer hides a diagram or
  records the wrong image. When a tag repeats an attribute, the last value
  is used, as in the HTML extractor.
- Markdown: a numeric character reference of more than 4300 digits in a
  raw-HTML attribute no longer stops extraction with an error.

### Compatibility

- A user who edited or deleted the installed `README.md` gets
  `modified managed files` on upgrade. Run `uninstall --force` and then
  install again; a plain install over a modified target is also refused.
- A run folder made with 0.2.4 from a Markdown source whose media list
  changed fails reproduction (`reproduction.mismatch`) until the source is
  re-extracted and the evidence rebuilt, because the verifier compares the
  whole manifest, including its media list. That happens when an image link
  destination uses a character reference that changes the file extension or
  the fragment (`plot&#46;png`, `p&num;.png`), or when raw HTML repeats an
  attribute or has an attribute name inside another attribute's value.

## 0.2.4 - 2026-11-08

- Verifier: it deletes an existing `dod.json` file in the run root before it
  writes a new one, so a run that fails after that point leaves no stale
  passing file. The exit code stays the authority: a read-only or symlinked
  `dod.json` still fails the run (exit 1) and is left in place.
- Verification of very large runs (tens of thousands of chunks) is much faster.
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
