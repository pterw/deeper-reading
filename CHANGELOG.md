# Changelog

## 0.2.3 — prepared, not published

Combines the v0.2.2 structured-verification work with installer and script hardening.

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

This is a release candidate; no release tag or package publication is implied.
